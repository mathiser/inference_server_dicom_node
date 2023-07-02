import datetime
import json
import logging
import os
import queue
import shutil
import tarfile
import tempfile
import threading
import tarfile
import time
from io import BytesIO
from typing import List

from daemon.fingerprinting.fingerprint import fast_fingerprint, slow_fingerprint
from database.db import DB
from database.models import Task
from decorators.logging import log
from dicom_networking.scp import SCP
from dicom_networking.scu import post_folder_to_dicom_node

class Daemon(threading.Thread):
    def __init__(self, client, db: DB, scp: SCP, run_interval: int = 10, timeout: int = 7200, log_level=10):
        super().__init__()
        self.client = client
        self.db = db
        self.scp = scp
        self.run_interval = run_interval
        self.timeout = datetime.timedelta(seconds=timeout)
        self.running = True

        LOG_FORMAT = ('%(levelname)s:%(asctime)s:%(message)s')
        logging.basicConfig(level=log_level, format=LOG_FORMAT)
        self.logger = logging.getLogger(__name__)


    @log
    def kill(self):
        self.logger.debug(f"Killing daemon")
        self.running = False

    @log
    def tar_dirs(self, tar_path, paths: List):
        with tarfile.TarFile.open(tar_path, mode="w") as tf:
            for path in paths:
                tf.add(path, arcname=os.path.basename(path))
    @log
    def fingerprint(self):
        fps = list(self.db.get_fingerprints())
        waiting = True
        while waiting:
            try:
                assoc = self.scp.get_incoming_queue().get(timeout=self.run_interval)
                self.logger.info(f"Running fingerprinting on assoc_id: {assoc}")

                for fp in fps:
                    # if fast_fingerprint(assoc=assoc, fp=fp):
                    matching_series_instances = slow_fingerprint(assoc=assoc, fp=fp)
                    if matching_series_instances:
                        task = self.db.add_task(fingerprint_id=fp.id)
                        self.logger.info(f"Fingerprint match: {task.__dict__}")

                        matching_series_instance_paths = list([os.path.dirname(matching_series_instance.path) for matching_series_instance in
                                          matching_series_instances])

                        self.logger.info(f"tarping up {matching_series_instance_paths} for task: {task.__dict__}")
                        self.tar_dirs(tar_path=task.tar_path,
                                      paths=matching_series_instance_paths)
                # Escape function if incomings are all fingerprinted
                if self.scp.get_incoming_queue().empty():
                    waiting = False

            # Escape if nothing has arrived in a while.
            except queue.Empty:
                waiting = False

    @log
    def post_tasks(self):
        tasks = list(self.db.get_tasks_by_kwargs({"status": 0}))
        for task in tasks:
            # Post to inference_server
            res = self.client.post_task(task)
            self.logger.debug(res)
            if res.ok:
                res_task = json.loads(res.content)
                print(res_task)
                self.db.update_task(task_id=task.id, status=1, inference_server_uid=res_task["inference_server_uid"])
            else:
                self.db.update_task(task_id=task.id, status=-1)  # Tag for deletion

    @log
    def is_retirement_ready(self, timestamp: datetime.datetime):
        return (datetime.datetime.now() - timestamp) > self.timeout

    @log
    def retire_tasks(self):
        tasks = list(self.db.get_tasks())
        for task in tasks:
            if task.status not in [10, 11, -1]:
                if self.is_retirement_ready(task.timestamp):
                    self.logger.info(f"Retiring task: {task.__dict__}")
                    self.db.update_task(task_id=task.id,
                                        status=-1)


    @log
    def get_tasks(self):
        tasks = list(self.db.get_tasks_by_kwargs({"status": 1}))
        for task in tasks:
            print(task.inference_server_uid)
            res = self.client.get_task(task)

            if res.ok:
                self.logger.info(f"Task: {task.inference_server_uid} was retrieved successfully")
                with open(task.inference_server_tar, "bw") as f:
                    f.write(res.content)
                self.db.update_task(task_id=task.id, status=2)  # Ready to post to destinations

            elif res.status_code in [551, 554]:
                self.logger.info(
                    f"Task: {task.inference_server_uid}, seems to be on the way, but not finished yet")

            elif res.status_code in [405, 500, 552, 553]:
                self.logger.error(
                    f"Task: {task.inference_server_uid}, has failed with status code {res.status_code}")
                self.db.update_task(task.id, status=3)
            else:
                self.logger.info(
                    f"This status code should not be possible for Task: {task.inference_server_uid}. Go talk to an admin")

    @log
    def post_to_final_destinations(self):
        tasks = list(self.db.get_tasks_by_kwargs({"status": 2}))
        for task in tasks:
            self.logger.info(f"Posting task {task.__dict__} to final destination")
            with tempfile.TemporaryDirectory() as tmp_dir:
                shutil.unpack_archive(task.inference_server_tar, extract_dir=tmp_dir)
                if len(task.fingerprint.destinations) == 0:
                    self.db.update_task(task.id, status=3)
                else:
                    for destination in task.fingerprint.destinations:
                        post_folder_to_dicom_node(scu_ip=destination.scu_ip,
                                                  scu_port=destination.scu_port,
                                                  scu_ae_title=destination.scu_ae_title,
                                                  dicom_dir=tmp_dir)
                        self.db.update_task(task.id, status=3)

    @log
    def clean_up(self):
        # Succesful tasks
        tasks = list(self.db.get_tasks_by_kwargs({"status": 3}))
        self.delete_files(tasks, 10)  # Final success status

        tasks = list(self.db.get_tasks_by_kwargs({"status": -1}))
        self.delete_files(tasks, 11)  # Final status for failed tasks

    @log
    def delete_files(self, tasks: List[Task], final_task_status: int):
        for task in tasks:
            self.logger.info(f"Running deletion for {task.__dict__}")
            # For local files
            if task.fingerprint.delete_locally and not task.deleted_local:  # Delete if fingerprint dictates to do so
                if os.path.isfile(task.tar_path):
                    self.logger.info(f"Deleting {task.tar_path}")
                    os.remove(task.tar_path)
                if os.path.isfile(task.inference_server_tar):
                    self.logger.info(f"Deleting {task.inference_server_tar}")
                    os.remove(task.inference_server_tar)
                self.db.update_task(task.id, deleted_local=True)

            # For remote files (on inference server)
            if task.fingerprint.delete_remotely and not task.deleted_remote:
                self.logger.info(f"Deleting remotely: {task.inference_server_uid}")
                self.client.delete_task(task)
                self.db.update_task(task.id, deleted_remote=True)

            # Update status to final_task_status. This indicates that task deletion has been considered
            self.logger.info(f"Updating {task.__dict__} to status {final_task_status}")
            self.db.update_task(task.id, status=final_task_status)


    def run(self):
        while self.running:
            self.retire_tasks()
            self.fingerprint()
            self.post_tasks()
            self.get_tasks()
            self.post_to_final_destinations()
            self.clean_up()