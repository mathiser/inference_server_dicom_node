import datetime
import json
import logging
import os
import shutil
import tempfile
import threading
import zipfile
import time
from daemon.fingerprinting.fingerprint import fast_fingerprint, slow_fingerprint
from database.db import DB
from database.models import Task
from dicom_networking.scp import SCP
from dicom_networking.scu import post_folder_to_dicom_node


class Daemon(threading.Thread):
    def __init__(self, client, db: DB, scp: SCP, run_interval: int = 10, timeout: int = 7200):
        super().__init__()
        self.client = client
        self.db = db
        self.scp = scp
        self.run_interval = run_interval
        self.timeout = datetime.timedelta(seconds=timeout)
        self.running = True
    def kill(self):
        self.running = False

    def zipdirs(self, zip_path, paths):
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for path in paths:
                # ziph is zipfile handle
                for root, dirs, files in os.walk(path):
                    for file in files:
                        zipf.write(os.path.join(root, file),
                                   os.path.relpath(os.path.join(root, file),
                                                   os.path.join(path, '..')))

    def fingerprint(self):
        fps = list(self.db.get_fingerprints())
        while not self.scp.get_incoming_queue().empty():
            assoc = self.scp.get_incoming_queue().get(block=True)
            for fp in fps:
                if fast_fingerprint(assoc=assoc, fp=fp):
                    matching_series_instances = slow_fingerprint(assoc=assoc, fp=fp)
                    if matching_series_instances:
                        task = self.db.add_task(fingerprint_id=fp.id)
                        self.zipdirs(zip_path=task.zip_path,
                                     paths=list(
                                         [os.path.dirname(matching_series_instance.path) for matching_series_instance in
                                          matching_series_instances]))

    def post_tasks(self):
        tasks = list(self.db.get_tasks_by_kwargs({"status": 0}))
        for task in tasks:
            # Post to inference_server
            res = self.client.post_task(task)
            if res.ok:
                uid = json.loads(res.content)
                self.db.update_task(task_id=task.id, status=1, inference_server_uid=uid)
            else:
                self.db.update_task(task_id=task.id, status=-1)  # Tag for deletion


    def is_retirement_ready(self, timestamp: datetime.datetime):
        print(datetime.datetime.now() - timestamp)
        return (datetime.datetime.now() - timestamp) > self.timeout

    def retire_task(self, task: Task):
        self.db.update_task(task_id=task.id,
                            status=-1)

    def get_tasks(self):
        tasks = list(self.db.get_tasks_by_kwargs({"status": 1}))
        for task in tasks:
            if self.is_retirement_ready(task.timestamp):
                print("ooooold")
                self.retire_task(task)
                continue

            res = self.client.get_task(task)

            if res.ok:
                logging.info(f"Task: {task.inference_server_uid} was retrieved successfully")
                with open(task.inference_server_zip, "bw") as f:
                    f.write(res.content)
                self.db.update_task(task_id=task.id, status=2)  # Ready to post to destinations

            elif res.status_code in [551, 554]:
                logging.info(
                    f"Task: {task.inference_server_uid}, seems to be on the way, but not finished yet")

            elif res.status_code in [500, 552, 553]:
                logging.error(
                    f"Task: {task.inference_server_uid}, has failed with status code {res.status_code}")
                self.db.update_task(task.id, status=-1)
            else:
                logging.info(
                    f"This status code should not be possible for Task: {task.inference_server_task.uid}. Go talk to an admin")

    def post_to_final_destinations(self):
        tasks = list(self.db.get_tasks_by_kwargs({"status": 2}))
        for task in tasks:
            with tempfile.TemporaryDirectory() as tmp_dir:
                shutil.unpack_archive(task.inference_server_zip, extract_dir=tmp_dir)
                for destination in task.fingerprint.destinations:
                    post_folder_to_dicom_node(scu_ip=destination.scu_ip,
                                              scu_port=destination.scu_port,
                                              scu_ae_title=destination.scu_ae_title,
                                              dicom_dir=tmp_dir)
                    self.db.update_task(task.id, status=3)

    def delete_local(self):
        tasks = list(self.db.get_tasks_by_kwargs({"status": 3, "deleted_local": False}))
        tasks += list(self.db.get_tasks_by_kwargs({"status": -1, "deleted_local": False}))
        for task in tasks:
            if os.path.isfile(task.zip_path):
                shutil.rmtree(task.zip_path)
            if os.path.isfile(task.inference_server_zip):
                shutil.rmtree(task.inference_server_zip)
            self.db.update_task(task.id, deleted_local=True)

    def delete_remote(self):
        tasks = list(self.db.get_tasks_by_kwargs({"status": 3, "deleted_remote": False}))
        tasks += list(self.db.get_tasks_by_kwargs({"status": -1, "deleted_remote": False}))

        for task in tasks:
            self.client.delete_task(task)
            self.db.update_task(task.id, deleted_remote=True)

    def run(self):
        while self.running:
            time.sleep(self.run_interval)
            self.fingerprint()
            self.post_tasks()
            self.get_tasks()
            self.post_to_final_destinations()
            self.delete_remote()
            self.delete_local()
