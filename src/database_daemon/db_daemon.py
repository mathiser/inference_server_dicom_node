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
from fingerprint_database.fingerprint_database import FingerprintDatabase
from dicom_networking import scu

LOG_FORMAT = ('%(levelname)s:%(asctime)s:%(message)s')
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


class DBDaemon:
    def __init__(self,
                 client,
                 db: DB,
                 fp: FingerprintDatabase,
                 daemon_run_interval_secs: int,
                 task_expire_after_secs: int,
                 incoming_idle_after_secs: int,
                 incoming_expire_after_secs: int,
                 ):
        self.daemon_run_interval_secs = daemon_run_interval_secs
        self.incoming_idle_after_secs = incoming_idle_after_secs
        self.task_expire_after_secs = task_expire_after_secs
        self.incoming_expire_after_secs = incoming_expire_after_secs
        self.db = db
        self.fp = fp
        self.client = client

    def run_set_idle_flag_on_incomings(self):
        incs = self.db.get_incomings_by_kwargs({"is_deleted": False, "is_idle": False})
        for inc in incs:
            if (datetime.datetime.now() - inc.last_timestamp) > datetime.timedelta(
                    seconds=self.incoming_idle_after_secs):
                self.db.update_incoming(incoming_id=inc.id, is_idle=True)

    def run_expire_tasks(self):
        tasks = self.db.get_tasks_by_kwargs({"is_deleted": False, "is_idle": True})
        for task in tasks:
            if (datetime.datetime.now() - task.last_timestamp) > datetime.timedelta(
                    seconds=self.task_expire_after_secs):
                self.db.update_task(task_id=task.id, status=50,
                                    is_deleted=True)  # Status 50 is "to be deleted on inference server"

    def run_fingerprint_tasks(self):
        pids = set([inc.PatientID for inc in self.db.get_incomings_by_kwargs({"is_deleted": False, "is_idle": True})])  # To allow patient-wise fingerprinting
        for pid in pids:
            for fp in self.fp.get_fingerprints():
                self.get_all_matching_incomings_from_fingerprint(pid=pid, fingerprint=fp)

    def run_post_tasks(self):
        tasks = self.db.get_tasks_by_status(0)
        for task in tasks:

            # Post to inference_server
            res = self.client.post_task(task)

            if res.ok:
                uid = json.loads(res.content)
                self.db.add_inference_server_task(task_id=task.id, uid=uid)

                # Update status
                self.db.update_task(task.id, status=1)  # Tag for getting
            else:
                self.db.update_task(task_id=task.id, status=50)  # Tag for deletion

    def run_delete_fingerprinted_incomings(self):
        # Delete all incs after all fingerprints have been matched
        incs = self.db.get_incomings_by_kwargs({"is_deleted": False, "is_idle": True})
        for inc in incs:
            self.db.update_incoming(incoming_id=inc.id, is_deleted=True)

    def get_all_matching_incomings_from_fingerprint(self, pid, fingerprint):
        # Container for matches
        matches = list([None for n in range(len(fingerprint.sub_fingerprints))])

        # Loop over sub_fingerprints to find matches
        for i, sub_fingerprint in enumerate(fingerprint.sub_fingerprints):
            # DB call to find match
            inc = self.db.get_incoming_by_fingerprint(
                patient_id=pid,
                modality_exp=sub_fingerprint["modality_exp"],
                sop_class_uid_exp=sub_fingerprint["sop_class_uid_exp"],
                series_description_exp=sub_fingerprint["series_description_exp"],
                study_description_exp=sub_fingerprint["study_description_exp"],
                exclude_exp=sub_fingerprint["exclude_exp"])

            # If nothing is found, do not insert anything to matches, and None will prevail
            if inc is None:
                return
            else:
                matches[i] = {"sub_fingerprint": sub_fingerprint,  # Match defeats None
                              "incoming": inc}

        assert None not in matches  # All must be proper matches
        # If not stopped in the previous step, go ahead and add task
        task = self.db.add_task(model_human_readable_id=fingerprint.model_human_readable_id,
                                inference_server_url=fingerprint.inference_server_url)

        # Add all scus
        for scu in fingerprint.scus:
            self.db.add_destination(task_id=task.id,
                                    scu_port=scu.scu_port,
                                    scu_ae_title=scu.scu_ae_title,
                                    scu_ip=scu.scu_ip)

        # Add all matches as fingerprint matches
        for match in matches:
            incoming = match["incoming"]
            sub_fingerprint = match["sub_fingerprint"]

            self.db.add_fingerprint_match(task_id=task.id,
                                          incoming_id=incoming.id,
                                          sop_class_uid_exp=sub_fingerprint["sop_class_uid_exp"],
                                          series_description_exp=sub_fingerprint["series_description_exp"],
                                          study_description_exp=sub_fingerprint["study_description_exp"],
                                          exclude_exp=sub_fingerprint["exclude_exp"],
                                          modality_exp=sub_fingerprint["modality_exp"],
                                          zip_path=sub_fingerprint["zip_path"],
                                          )
        return task

    def run_get_tasks(self):
        tasks = self.db.get_tasks_by_status(2)
        for task in tasks:
            try:
                res = self.client.get_task(task)
                self.db.add_inference_server_response(task_id=task.id, status_code=res.status_code)

                if res.ok:
                    # If okay, go ahead and extract to a temporary file
                    with tempfile.TemporaryDirectory() as tmp_dir, zipfile.ZipFile(BytesIO(res.content),
                                                                                   "r") as zip_file:
                        zip_file.extractall(tmp_dir)

                        # Send it off to all destinations (Note that there is no fall back/resend on failed attempts.)
                        for destination in task.destinations:
                            if not destination.is_sent:
                                scu.post_folder_to_dicom_node(dicom_dir=tmp_dir, destination=destination)
                                self.db.update_destination(destination_id=destination.id, is_sent=True)

                    # Finally set status of task to 50 (ready to delete.)
                    self.db.update_task(task_id=task.id, status=50)  # Ready to delete

                elif res.status_code in [551, 554]:
                    logging.info(
                        f"Task: {task.inference_server_task.uid}, seems to be on the way, but not finished yet")

                elif res.status_code in [500, 552, 553]:
                    logging.error(
                        f"Task: {task.inference_server_task.uid}, has failed with status code {res.status_code}")
                    self.db.add_task_status(task.id, 50)

                else:
                    logging.info(
                        f"This status code should not be possible for Task: {task.inference_server_task.uid}. Go talk to an admin")

            except Exception as e:
                traceback.print_exc()
                print(e)

    def run_delete_tasks_from_inference_server(self):
        tasks = self.db.get_tasks_by_status(50)
        for task in tasks:
            res = self.client.delete_task(task)
            if res.ok:
                self.db.update_task(task_id=task.id, status=100, is_deleted=True)
                logging.info(
                    f"InferenceServer says that {task.inference_server_response.uid} has successfully been deleted")
            else:
                logging.error(
                    f"InferenceServer says that {task.inference_server_response.uid} is NOT deleted - please report this to admin")

    def main_loop(self):
        while True:
            self.run_set_idle_flag_on_incomings()
            self.run_fingerprint_tasks()
            self.run_post_tasks()
            self.run_delete_fingerprinted_incomings()
            self.run_get_tasks()
            self.run_delete_tasks_from_inference_server()
