import datetime
import os
import secrets
import shutil
import tempfile
import unittest
from typing import List

from database.db import DB
from models.models import Base
from fingerprint_handler.models import Fingerprint


class TestDB(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp()
        os.makedirs(self.tmp_dir, exist_ok=True)
        self.db = DB(data_dir=self.tmp_dir, declarative_base=Base)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir)

    def test_upsert_incoming(self):
        ## insert part
        timestamp = datetime.datetime.now()
        patient_id = secrets.token_urlsafe()
        modality = "MR"
        study_description = "1.2.3.4.5.6.7.8.9"
        series_description = "Some test series"
        sop_class_uid = "1.12.123.1234.12345"
        series_instance_uid = secrets.token_urlsafe()

        inc = self.db.upsert_incoming(timestamp=timestamp,
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
        inc = self.db.upsert_incoming(timestamp=new_timestamp,
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
        inc = self.test_upsert_incoming()
        echo_inc = self.db.get_incoming(inc.id)
        self.assertEqual(inc.id, echo_inc.id)
        self.assertEqual(inc.last_timestamp, echo_inc.last_timestamp)

    def test_get_incomings(self):
        incs = [self.test_upsert_incoming() for n in range(10)]
        echo_incs = self.db.get_incomings()
        self.assertEqual(len(incs), len(echo_incs))

    def test_get_incomings_by_kwargs(self):
        inc = self.test_upsert_incoming()
        echo_inc = self.db.get_incomings_by_kwargs({"id": inc.id, "last_timestamp": inc.last_timestamp})
        echo_inc = echo_inc[0]
        self.assertEqual(inc.is_deleted, echo_inc.is_deleted)
        self.assertEqual(inc.id, echo_inc.id)
        self.assertEqual(inc.last_timestamp, echo_inc.last_timestamp)
        self.assertEqual(inc.first_timestamp, echo_inc.first_timestamp)

    def test_set_incoming_toggles(self):
        inc = self.test_upsert_incoming()
        self.assertFalse(inc.is_deleted)
        self.db.set_incoming_toggles(inc.id, is_deleted=True)
        echo_inc = self.db.get_incoming(inc.id)
        self.assertTrue(echo_inc.is_deleted)

    def test_add_task(self):
        fp = Fingerprint(modality_regex="CT",
                          sop_class_uid_regex="",
                          exclude_regex="a^",
                          study_description_regex="COW|Something else",
                          series_description_regex="",
                          inference_server_url="http://localhost:8000/api/tasks/",
                          model_human_readable_id="cns_t1_oars")

        inc = self.test_upsert_incoming()

        task = self.db.add_task(incoming_id=inc.id,
                                modality_regex=fp.modality_regex,
                                exclude_regex=fp.exclude_regex,
                                study_description_regex=fp.study_description_regex,
                                inference_server_url=fp.inference_server_url,
                                series_description_regex=fp.series_description_regex,
                                sop_class_uid_regex=fp.sop_class_uid_regex,
                                model_human_readable_id=fp.model_human_readable_id)

        echo_task = self.db.get_task(task.id)

        self.assertEqual(echo_task.incoming.id, inc.id)
        self.assertIsInstance(echo_task.destinations, List)
        self.assertIsNone(echo_task.inference_server_response)
        self.assertEqual(len(echo_task.destinations), 0)
        self.assertIsNone(echo_task.inference_server_response, 0)

        return echo_task

    def test_get_task(self):
        task = self.test_add_task()
        echo_task = self.db.get_task(task.id)
        self.assertEqual(task.id, echo_task.id)
        self.assertEqual(task.incoming_id, echo_task.incoming_id)
        self.assertEqual(task.modality_regex, echo_task.modality_regex)
        self.assertEqual(task.model_human_readable_id, echo_task.model_human_readable_id)
        self.assertEqual(task.inference_server_url, echo_task.inference_server_url)
        self.assertEqual(task.inference_server_response, echo_task.inference_server_response)
        self.assertEqual(task.destinations, echo_task.destinations)
        self.assertEqual(task.exclude_regex, echo_task.exclude_regex)

    def test_get_task_by_kwargs(self):
        self.assertEqual(len(self.db.get_tasks_by_kwargs({"is_deleted": False})), 0)
        self.test_add_task()
        task = self.test_add_task()

        echo_tasks = self.db.get_tasks_by_kwargs({"is_deleted": False})
        self.assertEqual(len(self.db.get_tasks_by_kwargs({"is_deleted": False})), 2)

    def test_set_task_toggles(self):
        task = self.test_add_task()
        self.assertFalse(task.is_deleted)
        self.db.set_task_toggles(task.id, is_deleted=True)
        echo_inc = self.db.get_incoming(task.id)
        self.assertTrue(echo_inc.is_deleted)

    def test_set_task_status(self):
        task = self.test_add_task()
        self.assertEqual(task.status, 0)
        self.db.set_task_status(task_id=task.id, status=100)
        echo_task = self.db.get_task(task.id)
        self.assertEqual(echo_task.status, 100)

    def test_add_destination(self):
        task = self.test_add_task()
        dest = self.db.add_destination(
            task_id=task.id,
            scu_ip="127.0.0.1",
            scu_port=104,
            scu_ae_title="OTHER_ENDPOINT"
        )
        echo_task = self.db.get_task(task.id)
        self.assertEqual(echo_task.destinations[0].task_id, task.id)
        self.assertEqual(echo_task.destinations[0].scu_ip, dest.scu_ip)
        self.assertEqual(echo_task.destinations[0].scu_port, dest.scu_port)
        self.assertEqual(echo_task.destinations[0].scu_ae_title, dest.scu_ae_title)

    def test_add_inference_server_response(self):
        task = self.test_add_task()
        isr = self.db.add_inference_server_response(
            task_id=task.id,
            uid="1234567890987654321",
        )
        echo_task = self.db.get_task(task.id)
        self.assertEqual(echo_task.inference_server_response.task_id, isr.id)
        self.assertEqual(echo_task.inference_server_response.uid, isr.uid)
        self.assertIsNone(echo_task.inference_server_response.status_code)
        return isr

    def test_set_inference_server_response_status_code(self):
        isr = self.test_add_inference_server_response()
        self.db.set_inference_server_response_status_code(isr.id, 666)
        task = self.db.get_task(isr.task_id)
        self.assertEqual(task.inference_server_response.status_code, 666)

if __name__ == '__main__':
    unittest.main()
