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


def get_test_dicom(path):
    res = requests.get("https://xnat.bmia.nl/REST/projects/stwstrategyhn1/subjects/BMIAXNAT_S09203/experiments/BMIAXNAT_E62311/scans/1_3_6_1_4_1_40744_29_33371661027192187491509798061184654147/files?format=zip", stream=True)
    res_io = BytesIO(res.content)
    zf = zipfile.ZipFile(file=res_io)
    zf.extractall(path)
    return path

class TestSCP(unittest.TestCase):
    def setUp(self) -> None:
        self.test_case_dir = ".tmp/test_images/"
        if not os.path.isdir(self.test_case_dir):
            get_test_dicom(self.test_case_dir)
        self.tmp_dir = tempfile.mkdtemp(dir=".tmp/")

        self.scp = SCP(ae_title="DCM_ENDPOINT_AE",
                       ip="localhost",
                       port=11110,
                       storage_dir=self.tmp_dir)

        self.scp.run_scp(blocking=False)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir)
        self.scp.ae.shutdown()
        del self.scp

    def test_scp_and_post_to_dicom_node(self):
        self.assertTrue(os.path.exists(self.test_case_dir))
        self.assertTrue(post_folder_to_dicom_node(scu_ip=self.scp.ip, scu_port=self.scp.port, scu_ae_title=self.scp.ae_title, dicom_dir=self.test_case_dir))

    def test_scp_and_post_multiple_simultaneous_to_dicom_node(self):
        self.assertTrue(os.path.exists(self.test_case_dir))
        args = [(self.scp.ip, self.scp.port, self.scp.ae_title, self.test_case_dir) for i in range(4)]

        def post(scu_ip, scu_port, scu_ae_title, dicom_dir):
            self.assertTrue(post_folder_to_dicom_node(scu_ip=scu_ip, scu_port=scu_port, scu_ae_title=scu_ae_title, dicom_dir=dicom_dir))

        t = ThreadPool(4)
        t.starmap(post, args)
        t.close()
        t.join()

if __name__ == '__main__':
    unittest.main()
