import os
import shutil
import tempfile
import unittest

from database.db import DB
from database.models import Fingerprint, Trigger, Destination, DestinationFingerprintAssociation


class TestDB(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp()
        os.makedirs(self.tmp_dir, exist_ok=True)
        self.db = DB(base_dir=self.tmp_dir)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir)

    def test_add_fingerprint(self):
        fp = self.db.add_fingerprint(inference_server_url="https://awesome-server.org", human_readable_id="test")
        self.assertIsInstance(fp, Fingerprint)
        return fp

    def test_add_trigger(self):
        fp = self.test_add_fingerprint()
        trigger = self.db.add_trigger(fingerprint_id=fp.id,
                                      sop_class_uid_exact="1.12.123.1234.12345",
                                      study_description_pattern="1.2.3.4.5.6.7.8.9",
                                      series_description_pattern="Some test series")

        self.assertIsInstance(trigger, Trigger)
        fp = self.db.get_fingerprint(fp.id)
        self.assertEqual(1, len(fp.triggers))
        self.assertEqual(trigger.id, fp.triggers[0].id)
        return trigger

    def test_add_destination(self):
        #  fp = self.db.add_fingerprint()
        destination = self.db.add_destination(scu_ip="10.10.10.10",
                                              scu_port=104,
                                              scu_ae_title="TEST_AE")
        self.assertIsInstance(destination, Destination)
        # fp = self.db.add_destination_to_fingerprint(fp.id, destination.id)
        # self.assertEqual(1, len(fp.destinations))
        # self.assertEqual(destination.id, fp.destinations[0].id)
        return destination

    def test_add_destination_fingerprint_association(self):
        fp = self.test_add_fingerprint()
        dest = self.test_add_destination()
        self.db.add_destination_fingerprint_association(fingerprint_id=fp.id, destination_id=dest.id)

        echo_fp = self.db.get_fingerprint(fp.id)
        self.assertEqual(1, len(echo_fp.destinations))
        self.assertEqual(dest.id, echo_fp.destinations[0].id)
        return dest

    def test_add_task(self):
        fp = self.test_add_fingerprint()

        trigger = self.db.add_trigger(fingerprint_id=fp.id,
                                      sop_class_uid_exact="1.2.3.4.5.6.7.8.9",
                                      study_description_pattern="Some test series",
                                      series_description_pattern="1.12.123.1234.12345")

        destination = self.db.add_destination(scu_ip="10.10.10.10",
                                              scu_port=104,
                                              scu_ae_title="TEST_AE")
        self.db.add_destination_fingerprint_association(fingerprint_id=fp.id, destination_id=destination.id)

        task = self.db.add_task(fp.id)
        self.assertEqual(fp.id, task.fingerprint_id)

        self.assertEqual(trigger.id, task.fingerprint.triggers[0].id)
        self.assertEqual(destination.id, task.fingerprint.destinations[0].id)
        return task

    def test_update_task(self):
        task = self.test_add_task()
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
        return echo_task


    def test_delete_destination(self):
        dest = self.test_add_destination()

        res = self.db.delete_destination(destination_id=dest.id)
        echo_dest = self.db.generic_get(Destination, dest.id)
        self.assertIsNone(echo_dest)

    def test_delete_fingerprint(self):
        task = self.test_add_task()
        fp = task.fingerprint
        triggers = fp.triggers
        destinations = fp.destinations
        self.db.delete_fingerprint(fp.id)
        self.assertIsNone(self.db.get_fingerprint(fp.id))
        self.assertIsNone(self.db.generic_get(Trigger, triggers[0].id))
        q = self.db.generic_get_all(DestinationFingerprintAssociation)
        self.assertEqual(0, q.filter_by(fingerprint_id=fp.id).count())


if __name__ == '__main__':
    unittest.main()
