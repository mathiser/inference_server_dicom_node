import json
import os
import shutil
import tempfile
import unittest

from fingerprint_handler.fingerprint_handler import FingerprintHandler
from database.tests.test_db import TestDB
from models.models import Incoming


class TestFingerprintHandler(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.fp_handler = FingerprintHandler(fingerprint_dir=self.tmp_dir)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir)

    def test_load_fingerprints(self):
        self.assertEqual(0, len(self.fp_handler.fingerprints))
        self.dump_fingerprint_to_folder(self.tmp_dir)
        self.fp_handler.load_fingerprints()
        self.assertEqual(1, len(self.fp_handler.fingerprints))

    def test_get_fingerprint_from_incoming(self):
        db_tests = TestDB()
        db_tests.setUp()
        inc = db_tests.test_upsert_incoming()
        fps = self.fp_handler.get_fingerprint_from_incoming(inc)
        self.assertEqual(0, len(fps))
        self.test_load_fingerprints()
        fps = self.fp_handler.get_fingerprint_from_incoming(inc)
        self.assertEqual(1, len(fps))

    def dump_fingerprint_to_folder(self, folder, fp=None):
        if not fp:
            fp = {"modality_regex": "MR",
              "sop_class_uid_regex": "1.12.123.1234.12345",
              "exclude_regex": "a^",
              "study_description_regex": "",
              "series_description_regex": "Test",
              "inference_server_url": "http://localhost:8000/api/tasks/",
              "model_human_readable_id": "cns_t1_oars",
              "scus": [{"scu_ip": "localhost",
                        "scu_port": 11110,
                        "scu_ae_title": "DICOM_ENDPOINT_AE"}
                       ]}

        with open(os.path.join(folder, "fingerprint.json"), "w") as f:
            f.write(json.dumps(fp))


if __name__ == '__main__':
    unittest.main()
