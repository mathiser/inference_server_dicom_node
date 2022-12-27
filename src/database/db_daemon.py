import datetime
import json
import logging
import os
import shutil
import tempfile
import traceback
import zipfile
from io import BytesIO

from client.client import Client
from database.db import DB
from fingerprint_handler.fingerprint_handler import FingerprintHandler
from dicom_networking import scu
LOG_FORMAT = ('%(levelname)s:%(asctime)s:%(message)s')
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


class DBDaemon:
    def __init__(self,
                 db: DB,
                 fp: FingerprintHandler,
                 daemon_run_interval_secs: int,
                 post_timeout_secs: int,
                 incoming_idle_after_secs: int,
                 incoming_expire_after_secs: int,
                 client):
        self.daemon_run_interval_secs = daemon_run_interval_secs
        self.incoming_idle_after_secs = incoming_idle_after_secs
        self.post_timeout_secs = post_timeout_secs
        self.incoming_expire_after_secs = incoming_expire_after_secs
        self.db = db
        self.fp = fp
        self.client = client

    def run_set_idle_flag_on_incomings(self):
        incs = self.db.get_incomings_by_kwargs({"is_deleted": False, "is_idle": False})
        for inc in incs:
            if (datetime.datetime.now() - inc.last_timestamp) > datetime.timedelta(
                    seconds=self.incoming_idle_after_secs):
                self.db.set_incoming_toggles(incoming_id=inc.id, is_idle=True)

    def run_delete_expired_incomings(self):
        incs = self.db.get_incomings_by_kwargs({"is_deleted": False})
        for inc in incs:
            if (datetime.datetime.now() - inc.last_timestamp) > datetime.timedelta(
                    seconds=self.incoming_expire_after_secs):
                try:
                    shutil.rmtree(inc.path)
                except Exception as e:
                    traceback.print_exc()
                    logging.error(e)
                finally:
                    if not os.path.isdir(inc.path):
                        self.db.set_incoming_toggles(incoming_id=inc.id, is_deleted=True)

    def run_fingerprinting_to_add_tasks(self):
        incs = self.db.get_incomings_by_kwargs({"is_deleted": False,
                                                "is_idle": True})
        for inc in incs:
            fps = self.fp.get_fingerprint_from_incoming(inc)
            for fp in fps:
                # Check whether this particular incoming has been run with this model.
                existing_tasks = self.db.get_tasks_by_kwargs({"incoming_id": inc.id,
                                                              "model_human_readable_id": fp.model_human_readable_id})
                if len(existing_tasks) == 0:
                    task = self.db.add_task(incoming_id=inc.id,
                                            series_description_regex=fp.series_description_regex,
                                            sop_class_uid_regex=fp.sop_class_uid_regex,
                                            model_human_readable_id=fp.model_human_readable_id,
                                            modality_regex=fp.modality_regex,
                                            exclude_regex=fp.exclude_regex,
                                            study_description_regex=fp.study_description_regex,
                                            inference_server_url=fp.inference_server_url)
                    for scu in fp.scus:
                        self.db.add_destination(task_id=task.id,
                                                scu_port=scu.scu_port,
                                                scu_ae_title=scu.scu_ae_title,
                                                scu_ip=scu.scu_ip)
                    self.db.set_task_status(task.id, 1)

    def run_post_tasks(self):
        tasks = self.db.get_tasks_by_kwargs({"status": 1})
        for task in tasks:
            res = self.client.post_task(task)
            if res.ok:
                print(res.content)
                self.db.add_inference_server_response(task_id=task.id, uid=json.loads(res.content))
                self.db.set_task_status(task_id=task.id, status=2)

    def run_get_tasks(self):
        tasks = self.db.get_tasks_by_kwargs({"status": 2, "is_deleted": False})
        for task in tasks:
            try:
                res = self.client.get_task(task)
                self.db.set_inference_server_response_status_code(task.id, res.status_code)

                if res.ok:
                    with tempfile.TemporaryDirectory() as tmp_dir, zipfile.ZipFile(BytesIO(res.content), "r") as zip_file:
                        zip_file.extractall(tmp_dir)

                        for destination in task.destinations:
                            scu.post_folder_to_dicom_node(dicom_dir=tmp_dir, destination=destination)

                    # Finally set status of task
                    task = self.db.set_task_status(task_id=task.id, status=3)
            except Exception as e:
                traceback.print_exc()
                print(e)

    def run_delete_from_inference_server(self):
        tasks = self.db.get_tasks_by_kwargs({"status": 3})
        for task in tasks:
            res = self.client.delete_task(task)
            if res.ok:
                logging.info(
                    f"InferenceServer says that {task.inference_server_response.uid} has successfully been deleted")
                self.db.set_task_toggles(task_id=task.id, is_deleted=True)
            else:
                logging.error(
                    f"InferenceServer says that {task.inference_server_response.uid} is NOT deleted - please report this to admin")

    def main_loop(self):
        while True:
            self.run_delete_expired_incomings()
            self.run_set_idle_flag_on_incomings()
            self.run_fingerprinting_to_add_tasks()
            self.run_post_tasks()
            self.run_get_tasks()

