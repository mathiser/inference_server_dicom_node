import os
import secrets
import shutil
import tempfile
import unittest

from database.db import DB
from database.models import Fingerprint, Trigger, Destination, InferenceServer, Incoming


class TestDB(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp()
        os.makedirs(self.tmp_dir, exist_ok=True)
        self.db = DB(data_dir=self.tmp_dir)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir)

    def test_add_fingerprint(self):
        fp = self.db.add_fingerprint()
        print(fp)
        self.assertIsInstance(fp, Fingerprint)

    def test_add_trigger(self):
        fp = self.db.add_fingerprint()

        study_description_regex = "1.2.3.4.5.6.7.8.9"
        series_description_regex = "Some test series"
        sop_class_uid_regex = "1.12.123.1234.12345"

        trigger = self.db.add_trigger(fingerprint_id=fp.id,
                                      sop_class_uid_regex=sop_class_uid_regex,
                                      study_description_regex=study_description_regex,
                                      series_description_regex=series_description_regex)

        self.assertIsInstance(trigger, Trigger)
        fp = self.db.get_fingerprint(fp.id)
        self.assertEqual(1, len(fp.triggers))
        self.assertEqual(trigger.id, fp.triggers[0].id)

    def test_add_destination(self):
        fp = self.db.add_fingerprint()
        destination = self.db.add_destination(fp.id,
                                              scu_ip="10.10.10.10",
                                              scu_port=104,
                                              scu_ae_title="TEST_AE")
        self.assertIsInstance(destination, Destination)
        fp = self.db.get_fingerprint(fp.id)
        self.assertEqual(1, len(fp.destinations))
        self.assertEqual(destination.id, fp.destinations[0].id)

    def test_add_inference_server(self):
        fp = self.db.add_fingerprint()
        inference_server = self.db.add_inference_server(fingerprint_id=fp.id,
                                                        model_human_readable_id="Some Model",
                                                        inference_server_url="https://zip-it.com.org")
        fp = self.db.get_fingerprint(fp.id)
        self.assertEqual(inference_server.id, fp.inference_server.id)

    def test_add_incoming(self):
        incoming = self.db.add_incoming("123", "/some/path")
        self.assertIsInstance(incoming, Incoming)
        echo_incoming = self.db.get_incoming(incoming.id)
        self.assertEqual(incoming.zip_path, echo_incoming.zip_path)

    def test_get_incomings(self):
        incs = [self.db.add_incoming(str(n), str(n)) for n in range(10)]
        echo_incs = self.db.get_incomings()
        self.assertEqual(len(incs), echo_incs.count())

    def test_add_task(self):
        fp = self.db.add_fingerprint()

        trigger = self.db.add_trigger(fingerprint_id=fp.id,
                                      sop_class_uid_regex="1.2.3.4.5.6.7.8.9",
                                      study_description_regex="Some test series",
                                      series_description_regex="1.12.123.1234.12345")

        destination = self.db.add_destination(fp.id,
                                              scu_ip="10.10.10.10",
                                              scu_port=104,
                                              scu_ae_title="TEST_AE")

        inference_server = self.db.add_inference_server(fingerprint_id=fp.id,
                                                        model_human_readable_id="Some Model",
                                                        inference_server_url="https://zip-it.com.org")

        incoming = self.db.add_incoming("123", "/some/path")
        task = self.db.add_task(fp.id, incoming.id)
        self.assertEqual(incoming.id, task.incoming_id)
        self.assertEqual(fp.id, task.fingerprint_id)

        self.assertEqual(trigger.id, task.fingerprint.triggers[0].id)
        self.assertEqual(destination.id, task.fingerprint.destinations[0].id)
        self.assertEqual(inference_server.id, task.fingerprint.inference_server.id)
    def test_update_task(self):
        fp = self.db.add_fingerprint()

        trigger = self.db.add_trigger(fingerprint_id=fp.id,
                                      sop_class_uid_regex="1.2.3.4.5.6.7.8.9",
                                      study_description_regex="Some test series",
                                      series_description_regex="1.12.123.1234.12345")

        destination = self.db.add_destination(fp.id,
                                              scu_ip="10.10.10.10",
                                              scu_port=104,
                                              scu_ae_title="TEST_AE")

        inference_server = self.db.add_inference_server(fingerprint_id=fp.id,
                                                        model_human_readable_id="Some Model",
                                                        inference_server_url="https://zip-it.com.org")

        incoming = self.db.add_incoming("123", "/some/path")
        task = self.db.add_task(fp.id, incoming.id)
        self.assertFalse(task.deleted_remote)
        self.assertFalse(task.deleted_local)
        self.assertIsNone(task.inference_server_uid)
        self.assertEqual(task.status, 0)

        self.db.update_task(task_id=task.id,
                            inference_server_uid="ABC",
                            deleted_remote=True,
                            deleted_local=True,
                            status=2)
        echo_task = self.db.get_tasks_by_kwargs({"id": task.id}).first()
        self.assertTrue(echo_task.deleted_remote)
        self.assertTrue(echo_task.deleted_local)
        self.assertEqual(echo_task.inference_server_uid, "ABC")
        self.assertEqual(echo_task.status, 2)


if __name__ == '__main__':
    unittest.main()
