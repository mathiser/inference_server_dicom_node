import json
import os
import shutil
import tempfile
import unittest

from fingerprint_database.fingerprint_database import FingerprintDatabase


class TestFingerprintHandler(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.fp_handler = FingerprintDatabase(fingerprint_dir=self.tmp_dir)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir)

    def test_load_fingerprints(self):
        self.assertEqual(0, len(self.fp_handler.fingerprints))
        self.dump_fingerprint_to_folder(self.tmp_dir)
        self.fp_handler.load_fingerprints()
        self.assertEqual(1, len(self.fp_handler.fingerprints))

    def dump_fingerprint_to_folder(self, folder, fp=None):
        if not fp:
            shutil.copy2("./test_fingerprint.json", os.path.join(folder, "test_fingerprint.json"))
        else:
            with open(os.path.join(folder, "fp.json"), "w") as f:
                f.write(json.dumps(fp))

if __name__ == '__main__':
    unittest.main()
