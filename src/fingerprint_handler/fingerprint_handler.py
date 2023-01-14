import json
import logging
import os
import re
from typing import List

from fingerprint_handler.models import Fingerprint
from models.models import Incoming


class FingerprintHandler:
    def __init__(self, fingerprint_dir):
        self.fingerprint_dir = fingerprint_dir
        self.fingerprints = []
        self.load_fingerprints()

    def load_fingerprints(self):
        for fol, subs, files in os.walk(self.fingerprint_dir):
            for file in files:
                if file.endswith(".json"):
                    file_path = os.path.join(fol, file)
                    try:
                        with open(file_path, "r") as r:
                            fp_dict = json.loads(r.read())
                            fp = Fingerprint.parse_obj(fp_dict)
                            self.fingerprints.append(fp)
                    except Exception as e:
                        logging.error(e)

        if len(self.fingerprints) == 0:
            logging.info("No fingerprints found")
        else:
            logging.info(f"Found the following fingerprints:")
            for i, fp in enumerate(self.fingerprints):
                logging.info(f"{str(i)}: {str(fp)}")

    def get_fingerprints(self):
        return self.fingerprints
