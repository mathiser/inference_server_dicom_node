import datetime
import os.path
import shutil
import tempfile
import unittest
import zipfile
from io import BytesIO
from multiprocessing.pool import ThreadPool

import requests

from dicom_networking.scp import SCP
from dicom_networking.scu import post_folder_to_dicom_node


def get_test_dicom(path, url):
    res = requests.get(url)
    res_io = BytesIO(res.content)
    zf = zipfile.ZipFile(file=res_io)
    zf.extractall(path)
    return path

class TestSCP(unittest.TestCase):
    def setUp(self) -> None:
        os.makedirs(".tmp", exist_ok=True)
        self.tmp_dir = tempfile.mkdtemp(dir=".tmp", prefix=f"{datetime.datetime.now()}_")

        self.test_case_dir = ".tmp/test_images/"
        if not os.path.isdir(self.test_case_dir):
            get_test_dicom(path=self.test_case_dir, url="https://xnat.bmia.nl/REST/projects/stwstrategyhn1/subjects/BMIAXNAT_S09203/experiments/BMIAXNAT_E62311/scans/1_3_6_1_4_1_40744_29_33371661027192187491509798061184654147/files?format=zip")
            get_test_dicom(path=self.test_case_dir, url="https://www.rubomedical.com/dicom_files/dicom_viewer_Mrbrain.zip")
        self.tmp_source = os.path.join(self.tmp_dir, "source")
        os.makedirs(self.tmp_source)
        self.scp = SCP(ae_title="SOURCE",
                       ip="localhost",
                       port=11110,
                       temporary_storage=self.tmp_source,
                       pynetdicom_log_level="Normal",
                       log_level=20)

        self.scp.run_scp(blocking=False)

    def tearDown(self) -> None:
        self.scp.ae.shutdown()
        shutil.rmtree(self.tmp_dir)
        del self.scp

    def test_scp_and_post_multiple_simultaneous_to_dicom_node(self):
        self.assertTrue(os.path.exists(self.test_case_dir))
        args = [(self.scp.ip, self.scp.port, self.scp.ae_title, self.test_case_dir) for i in range(2)]

        def post(scu_ip, scu_port, scu_ae_title, dicom_dir):
            self.assertTrue(post_folder_to_dicom_node(scu_ip=scu_ip, scu_port=scu_port, scu_ae_title=scu_ae_title, dicom_dir=dicom_dir))
        t = ThreadPool(2)
        t.starmap(post, args)
        t.close()
        t.join()
        self.assertGreater(len(os.listdir(self.tmp_source)), 0)


if __name__ == '__main__':
    unittest.main()
