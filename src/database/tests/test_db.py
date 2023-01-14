import datetime
import os
import secrets
import shutil
import tempfile
import unittest

from database.db import DB
from models.models import Base


class TestDB(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp()
        os.makedirs(self.tmp_dir, exist_ok=True)
        self.db = DB(data_dir=self.tmp_dir, declarative_base=Base)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir)

    def test_burst_insert_incoming(self, patient_id=None):
        ## insert part
        timestamp = datetime.datetime.now()
        if not patient_id:
            patient_id = secrets.token_urlsafe()
        modality = "MR"
        study_description = "1.2.3.4.5.6.7.8.9"
        series_description = "Some test series"
        sop_class_uid = "1.12.123.1234.12345"
        series_instance_uid = secrets.token_urlsafe()

        inc = self.db.burst_insert_incoming(timestamp=timestamp,
                                            patient_id=patient_id,
                                            modality=modality,
                                            study_description=study_description,
                                            series_description=series_description,
                                            sop_class_uid=sop_class_uid,
                                            series_instance_uid=series_instance_uid)

        self.assertEqual(inc.first_timestamp, timestamp)
        self.assertEqual(inc.last_timestamp, timestamp)
        self.assertEqual(inc.PatientID, patient_id)
        self.assertEqual(inc.Modality, modality),
        self.assertEqual(inc.SeriesDescription, series_description)
        self.assertEqual(inc.StudyDescription, study_description)
        self.assertEqual(inc.SOPClassUID, sop_class_uid)
        self.assertFalse(inc.is_deleted)
        self.assertFalse(inc.is_idle)
        # Update part
        new_timestamp = datetime.datetime.now()
        inc = self.db.burst_insert_incoming(timestamp=new_timestamp,
                                            patient_id=patient_id,
                                            modality=modality,
                                            study_description=study_description,
                                            series_description=series_description,
                                            sop_class_uid=sop_class_uid,
                                            series_instance_uid=series_instance_uid)

        self.assertFalse(inc.is_idle)
        self.assertEqual(inc.first_timestamp, timestamp)
        self.assertEqual(inc.last_timestamp, new_timestamp)
        self.assertEqual(inc.PatientID, patient_id)
        self.assertEqual(inc.Modality, modality),
        self.assertEqual(inc.SeriesDescription, series_description)
        self.assertEqual(inc.StudyDescription, study_description)
        self.assertEqual(inc.SOPClassUID, sop_class_uid)
        self.assertFalse(inc.is_deleted)
        return inc

    def test_get_incoming(self):
        inc = self.test_burst_insert_incoming()
        echo_inc = self.db.get_incoming(inc.id)
        self.assertEqual(inc.id, echo_inc.id)
        self.assertEqual(inc.last_timestamp, echo_inc.last_timestamp)

    def test_get_incomings(self):
        incs = [self.test_burst_insert_incoming() for n in range(10)]
        echo_incs = self.db.get_incomings()
        self.assertEqual(len(incs), len(echo_incs))

    def test_get_incomings_by_fingerprint(self):
        inc = self.test_burst_insert_incoming(patient_id="123")
        echo_inc = self.db.get_incoming_by_fingerprint(patient_id=inc.PatientID,
                                                       study_description_exp="2.3.4")
        self.assertIsNotNone(echo_inc)
        echo_inc = self.db.get_incoming_by_fingerprint(patient_id=inc.PatientID,
                                                       study_description_exp="2.3.4",
                                                       exclude_exp="MR")
        self.assertIsNone(echo_inc)
        self.test_burst_insert_incoming("123")
        self.assertWarns(UserWarning,
                         self.db.get_incoming_by_fingerprint,
                         patient_id=inc.PatientID,
                         study_description_exp="2.3.4")
        return echo_inc

    def test_get_incomings_by_kwargs(self):
        inc = self.test_burst_insert_incoming()
        echo_inc = self.db.get_incomings_by_kwargs({"id": inc.id, "last_timestamp": inc.last_timestamp})
        echo_inc = echo_inc[0]
        self.assertEqual(inc.is_deleted, echo_inc.is_deleted)
        self.assertEqual(inc.id, echo_inc.id)
        self.assertEqual(inc.last_timestamp, echo_inc.last_timestamp)
        self.assertEqual(inc.first_timestamp, echo_inc.first_timestamp)

    def test_update_incoming(self):
        inc = self.test_burst_insert_incoming()
        self.assertFalse(inc.is_deleted)
        self.db.update_incoming(inc.id, is_deleted=True)
        echo_inc = self.db.get_incoming(inc.id)
        self.assertTrue(echo_inc.is_deleted)

    def test_add_task(self):
        inference_server_url = "http://localhost:8000/api/tasks/"
        model_human_readable_id = "cns_t1_oars"

        task = self.db.add_task(inference_server_url=inference_server_url,
                                model_human_readable_id=model_human_readable_id)

        echo_task = self.db.get_task(task.id)

        self.assertEqual(echo_task.id, task.id)
        self.assertEqual(0, len(echo_task.destinations))
        self.assertIsNone(echo_task.inference_server_task)
        self.assertEqual(len(echo_task.fingerprint_matches), 0)

        return echo_task

    def test_get_task(self):
        task = self.test_add_task()
        echo_task = self.db.get_task(task.id)
        self.assertEqual(task.id, echo_task.id)
        self.assertEqual(task.model_human_readable_id, echo_task.model_human_readable_id)
        self.assertEqual(task.inference_server_url, echo_task.inference_server_url)
        self.assertIsNone(task.inference_server_task)
        self.assertEqual(task.destinations, echo_task.destinations)

    def test_get_task_by_kwargs(self):
        t = self.test_add_task()

        self.assertEqual(len(self.db.get_tasks_by_kwargs({"model_human_readable_id": t.model_human_readable_id})), 1)
        self.test_add_task()
        self.test_add_task()

        echo_tasks = self.db.get_tasks_by_kwargs({"model_human_readable_id": t.model_human_readable_id})
        self.assertEqual(len(echo_tasks), 3)
        pass

    def test_update_task_status(self):
        task = self.test_add_task()
        self.assertEqual(task.status, 0)
        self.db.update_task(task_id=task.id, status=100)
        echo_task = self.db.get_task(task.id)
        self.assertEqual(echo_task.status, 100)

    def test_add_destination(self, task=None):
        if not task:
            task = self.test_add_task()
        dest = self.db.add_destination(
            task_id=task.id,
            scu_ip="127.0.0.1",
            scu_port=104,
            scu_ae_title="OTHER_ENDPOINT"
        )
        echo_task = self.db.get_task(task.id)
        self.assertEqual(len(echo_task.destinations), 1)
        self.assertEqual(echo_task.destinations[0].task_id, task.id)
        self.assertEqual(echo_task.destinations[0].scu_ip, dest.scu_ip)
        self.assertEqual(echo_task.destinations[0].scu_port, dest.scu_port)
        self.assertEqual(echo_task.destinations[0].scu_ae_title, dest.scu_ae_title)

    def test_add_inference_server_task(self, task=None):
        if not task:
            task = self.test_add_task()
        isuid = self.db.add_inference_server_task(
            task_id=task.id,
            uid="1234567890987654321",
        )
        echo_task = self.db.get_task(task.id)
        self.assertEqual(echo_task.inference_server_task.task_id, isuid.task_id)
        self.assertEqual(echo_task.inference_server_task.uid, isuid.uid)
        return isuid

    def test_add_inference_server_response(self, task=None):
        if not task:
            task = self.test_add_task()
        ist = self.test_add_inference_server_task(task=task)
        isr = self.db.add_inference_server_response(task_id=ist.id,
                                                    status_code=200)

        echo_task = self.db.get_task(task.id)
        self.assertEqual(echo_task.inference_server_response.id, isr.id)

        isr1 = self.db.add_inference_server_response(task_id=ist.id,
                                                     status_code=200)

        echo_task = self.db.get_task(task.id)
        self.assertEqual(echo_task.inference_server_response.id, isr1.id)

    def test_add_fingerprint_match(self):
        inc = self.test_burst_insert_incoming()
        task = self.test_add_task()
        self.assertEqual(0, len(task.fingerprint_matches))
        fpm = self.db.add_fingerprint_match(incoming_id=inc.id,
                                            task_id=task.id,
                                            study_description_exp=inc.StudyDescription[2:6],
                                            series_description_exp=inc.SeriesDescription[1:4],
                                            modality_exp=inc.Modality,
                                            zip_path=inc.Modality,
                                            sop_class_uid_exp=inc.SOPClassUID[-4:],
                                            exclude_exp="")
        echo_task = self.db.get_task(task.id)
        self.assertEqual(1, len(echo_task.fingerprint_matches))
        self.assertEqual(fpm.id, echo_task.fingerprint_matches[0].id)

        fpm1 = self.db.add_fingerprint_match(incoming_id=inc.id,
                                             task_id=task.id,
                                             study_description_exp=inc.StudyDescription[2:6],
                                             series_description_exp=inc.SeriesDescription[1:4],
                                             modality_exp=inc.Modality,
                                             zip_path=inc.Modality,
                                             sop_class_uid_exp=inc.SOPClassUID[-5:-2],
                                             exclude_exp="hestfest")
        echo_task = self.db.get_task(task.id)
        self.assertEqual(2, len(echo_task.fingerprint_matches))
        self.assertEqual(fpm.id, echo_task.fingerprint_matches[0].id)
        self.assertEqual(fpm1.id, echo_task.fingerprint_matches[1].id)

    def test_get_tasks_by_status(self):
        task = self.test_add_task()
        status_tasks = self.db.get_tasks_by_status(0)

        self.assertEqual(1, len(status_tasks))
        self.db.update_task(task.id, status=1)

        status_tasks = self.db.get_tasks_by_status(0)
        self.assertEqual(0, len(status_tasks))


if __name__ == '__main__':
    unittest.main()
