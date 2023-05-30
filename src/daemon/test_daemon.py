import datetime
import os
import shutil
import tempfile
import unittest

from client.mock_client import MockClient
from daemon.daemon import Daemon
from database.db import DB
from dicom_networking.scp import SCP
from dicom_networking.scu import post_folder_to_dicom_node
from dicom_networking.tests.test_scp import get_test_dicom


class TestDBDaemon(unittest.TestCase):
    def setUp(self) -> None:
        os.makedirs(".tmp", exist_ok=True)
        self.tmp_db_base_dir = tempfile.mkdtemp(dir=".tmp", prefix=f"{datetime.datetime.now()}_")
        self.tmp_db_dir = os.path.join(self.tmp_db_base_dir, "database")
        os.makedirs(self.tmp_db_dir)
        self.db = DB(base_dir=self.tmp_db_dir)

        self.test_case_dir = ".tmp/test_images/"
        if not os.path.isdir(self.test_case_dir):
            get_test_dicom(self.test_case_dir)

        self.tmp_source = os.path.join(self.tmp_db_base_dir, "source")
        os.makedirs(self.tmp_source)
        self.scp = SCP(ae_title="SOURCE",
                       ip="localhost",
                       port=11110,
                       temporary_storage=self.tmp_source,
                       pynetdicom_log_level="Normal",
                       log_level=20
                       )

        self.tmp_destination = os.path.join(self.tmp_db_base_dir, "destination")
        os.makedirs(self.tmp_destination)
        self.destination = SCP(ae_title="DESTINATION",
                               ip="localhost",
                               port=11111,
                               temporary_storage=self.tmp_destination,
                               pynetdicom_log_level="Normal",
                               log_level=20
                               )

        self.scp.run_scp(blocking=False)
        self.destination.run_scp(blocking=False)
        self.client = MockClient()
        self.daemon = Daemon(client=self.client, db=self.db, scp=self.scp)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_db_base_dir)
        self.scp.ae.shutdown()
        self.destination.ae.shutdown()
        del self.scp, self.destination

    def test_fingerprint_match(self):
        fp = self.db.add_fingerprint(model_human_readable_id="test",
                                     inference_server_url="test")
        self.db.add_trigger(fingerprint_id=fp.id,
                            sop_class_uid_exact="1.2.840.10008.5.1.4.1.1.2")

        self.assertTrue(os.path.exists(self.test_case_dir))
        self.assertTrue(post_folder_to_dicom_node(scu_ip=self.scp.ip,
                                                  scu_port=self.scp.port,
                                                  scu_ae_title=self.scp.ae_title,
                                                  dicom_dir=self.test_case_dir))

        self.daemon.fingerprint()
        self.assertEqual(1, self.db.get_tasks().count())
        self.assertEqual(1, len(os.listdir(self.db.data_dir)))
        self.assertTrue(os.path.isfile(self.db.get_tasks().first().zip_path))


    def test_fingerprint_multi_model_match(self):
        fp = self.db.add_fingerprint(model_human_readable_id="test",
                                     inference_server_url="test")
        self.db.add_trigger(fingerprint_id=fp.id,
                            sop_class_uid_exact="1.2.840.10008.5.1.4.1.1.2")
        self.db.add_trigger(fingerprint_id=fp.id,
                            sop_class_uid_exact="1.2.840.10008.5.1.4.1.1.4")

        self.assertTrue(os.path.exists(self.test_case_dir))
        self.assertTrue(post_folder_to_dicom_node(scu_ip=self.scp.ip,
                                                  scu_port=self.scp.port,
                                                  scu_ae_title=self.scp.ae_title,
                                                  dicom_dir=self.test_case_dir))

        self.daemon.fingerprint()
        self.assertEqual(1, self.db.get_tasks().count())
        self.assertEqual(1, len(os.listdir(self.db.data_dir)))
        self.assertTrue(os.path.isfile(self.db.get_tasks().first().zip_path))

    def test_fingerprint_no_match(self):
        fp = self.db.add_fingerprint(model_human_readable_id="test",
                                     inference_server_url="test")
        self.db.add_trigger(fingerprint_id=fp.id,
                            sop_class_uid_exact="1.2.840.10008.5.1.4.1.1.1")

        self.assertTrue(os.path.exists(self.test_case_dir))
        self.assertTrue(post_folder_to_dicom_node(scu_ip=self.scp.ip,
                                                  scu_port=self.scp.port,
                                                  scu_ae_title=self.scp.ae_title,
                                                  dicom_dir=self.test_case_dir))

        self.assertEqual(0, self.db.get_tasks().count())
        self.daemon.fingerprint()
        self.assertEqual(0, self.db.get_tasks().count())
        self.assertEqual(0, len(os.listdir(self.db.data_dir)))

    def test_post_tasks_single_modal(self):
        fp = self.db.add_fingerprint(model_human_readable_id="test",
                                     inference_server_url="test")
        self.db.add_trigger(fingerprint_id=fp.id,
                            sop_class_uid_exact="1.2.840.10008.5.1.4.1.1.2")

        post_folder_to_dicom_node(scu_ip=self.scp.ip,
                                  scu_port=self.scp.port,
                                  scu_ae_title=self.scp.ae_title,
                                  dicom_dir=self.test_case_dir)
        self.daemon.fingerprint()
        self.assertEqual(1, self.db.get_tasks_by_kwargs({"status": 0}).count())
        self.assertEqual(0, self.db.get_tasks_by_kwargs({"status": 1}).count())
        self.daemon.post_tasks()
        self.assertEqual(0, self.db.get_tasks_by_kwargs({"status": 0}).count())
        self.assertEqual(1, self.db.get_tasks_by_kwargs({"status": 1}).count())
        task = self.db.get_tasks_by_kwargs({"status": 1}).first()
        self.assertIsNotNone(task.inference_server_uid)

    def generate_fp(self):
        fp = self.db.add_fingerprint(model_human_readable_id="test",
                                     inference_server_url="test")
        return fp

    def test_get_tasks_single_modal(self):
        fp = self.generate_fp()

        self.db.add_trigger(fingerprint_id=fp.id,
                            sop_class_uid_exact="1.2.840.10008.5.1.4.1.1.2")

        post_folder_to_dicom_node(scu_ip=self.scp.ip,
                                  scu_port=self.scp.port,
                                  scu_ae_title=self.scp.ae_title,
                                  dicom_dir=self.test_case_dir)
        self.daemon.fingerprint()
        self.assertEqual(1, self.db.get_tasks_by_kwargs({"status": 0}).count())
        self.assertEqual(0, self.db.get_tasks_by_kwargs({"status": 1}).count())
        self.daemon.post_tasks()
        self.assertEqual(0, self.db.get_tasks_by_kwargs({"status": 0}).count())
        self.assertEqual(1, self.db.get_tasks_by_kwargs({"status": 1}).count())
        task = self.db.get_tasks_by_kwargs({"status": 1}).first()
        self.assertIsNotNone(task.inference_server_uid)

        self.daemon.get_tasks()
        self.assertTrue(os.path.isfile(task.inference_server_zip))

    def test_post_to_final_destinations(self):
        fp = self.db.add_fingerprint(model_human_readable_id="test",
                                     inference_server_url="test")
        self.db.add_trigger(fingerprint_id=fp.id,
                            sop_class_uid_exact="1.2.840.10008.5.1.4.1.1.2")
        dest = self.db.add_destination(scu_ip=self.destination.ip,
                                scu_port=self.destination.port,
                                scu_ae_title=self.destination.ae_title)
        self.db.add_destination_to_fingerprint(fp.id, dest.id)
        post_folder_to_dicom_node(scu_ip=self.scp.ip,
                                  scu_port=self.scp.port,
                                  scu_ae_title=self.scp.ae_title,
                                  dicom_dir=self.test_case_dir)

        self.daemon.fingerprint()
        self.assertEqual(1, self.db.get_tasks_by_kwargs({"status": 0}).count())
        self.assertEqual(0, self.db.get_tasks_by_kwargs({"status": 1}).count())

        self.daemon.post_tasks()
        self.assertEqual(0, self.db.get_tasks_by_kwargs({"status": 0}).count())
        self.assertEqual(1, self.db.get_tasks_by_kwargs({"status": 1}).count())

        task = self.db.get_tasks_by_kwargs({"status": 1}).first()
        self.assertIsNotNone(task.inference_server_uid)

        self.daemon.get_tasks()
        self.assertEqual(0, self.db.get_tasks_by_kwargs({"status": 1}).count())
        self.assertEqual(1, self.db.get_tasks_by_kwargs({"status": 2}).count())

        self.daemon.post_to_final_destinations()
        self.assertEqual(0, self.db.get_tasks_by_kwargs({"status": 2}).count())
        self.assertEqual(1, self.db.get_tasks_by_kwargs({"status": 3}).count())

        self.assertNotEqual(0, os.listdir(self.tmp_destination))

if __name__ == '__main__':
    unittest.main()
