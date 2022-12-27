import os.path
import shutil
import tempfile
import time
import unittest

from database.db import DB
from dicom_networking.scp import SCP
from dicom_networking.scu import post_folder_to_dicom_node
from models.models import Base, Destination

class TestSCP(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp()
        self.db_dir = tempfile.mkdtemp()
        self.test_case_dir = "dicom_networking/tests/test_image"
        self.db = DB(data_dir=self.db_dir, declarative_base=Base)
        self.scp = SCP(ae_title="DCM_ENDPOINT_AE",
                       ip="localhost",
                       port=11110,
                       storage_dir=self.tmp_dir,
                       db=self.db)
        self.scp.run_scp(blocking=False)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir)
        shutil.rmtree(self.db_dir)
        self.scp.shutdown_ae()
        del self.scp
    def test_scp_and_post_to_dicom_node(self):
        self.assertEqual(len(self.db.get_incomings()), 0)
        dest = Destination(task_id=-1, scu_port=self.scp.port, scu_ae_title=self.scp.ae_title, scu_ip=self.scp.ip)
        self.assertTrue(os.path.exists(self.test_case_dir))
        self.assertTrue(post_folder_to_dicom_node(destination=dest, dicom_dir=self.test_case_dir))
        incs = self.db.get_incomings()
        self.assertEqual(2, len(incs))
        self.assertFalse(incs[0].is_idle)
        self.assertNotEqual(incs[0].path, incs[1].path)

    def test_multiple_posts_yield_same_cases(self):
        self.assertEqual(len(self.db.get_incomings()), 0)
        dest = Destination(task_id=-1, scu_port=self.scp.port, scu_ae_title=self.scp.ae_title, scu_ip=self.scp.ip)
        self.assertTrue(post_folder_to_dicom_node(destination=dest, dicom_dir=self.test_case_dir))
        time.sleep(1)
        self.assertTrue(post_folder_to_dicom_node(destination=dest, dicom_dir=self.test_case_dir))
        time.sleep(1)
        self.assertTrue(post_folder_to_dicom_node(destination=dest, dicom_dir=self.test_case_dir))

if __name__ == '__main__':
    unittest.main()
