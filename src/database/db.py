import datetime
import json
import logging
import os
import tempfile
from typing import List
import re
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from models import Fingerprint, Incoming, SCU


class DB:
    def __init__(self, fingerprint_dir):
        self.fingerprint_dir = fingerprint_dir
        self.fingerprints = []
        for fol, subs, files in os.walk(self.fingerprint_dir):
            for file in files:
                if file.endswith(".json"):
                    file_path = os.path.join(fol, file)
                    try:
                        with open(file_path, "r") as r:
                            fp_dict = json.loads(r.read())
                            fp = Fingerprint(modality_regex=fp_dict["modality_regex"],
                                             sop_class_uid_regex=fp_dict["sop_class_uid_regex"],
                                             study_description_regex=fp_dict["study_description_regex"],
                                             series_description_regex=fp_dict["series_description_regex"],
                                             inference_server_url=fp_dict["inference_server_url"],
                                             model_human_readable_id=fp_dict["model_human_readable_id"],
                                             scus=[SCU(**scu) for scu in fp_dict["scus"]])

                            self.fingerprints.append(fp)

                    except Exception as e:
                        logging.error(e)
        if len(self.fingerprints) == 0:
            logging.info("No fingerprints found")
        else:
            logging.info(f"Found the following fingerprints: {str(self.fingerprints)}")

    def get_fingerprints(self):
        return self.fingerprints

    def get_fingerprint_from_incoming(self, incoming: Incoming) -> List[Fingerprint]:
        to_return = []
        for fingerprint in self.fingerprints:
            modality_re = re.compile(r"{}".format(fingerprint.modality_regex), re.IGNORECASE)
            sop_class_uid_re = re.compile(r"{}".format(fingerprint.sop_class_uid_regex), re.IGNORECASE)
            series_re = re.compile(r"{}".format(fingerprint.series_description_regex), re.IGNORECASE)
            study_re = re.compile(r"{}".format(fingerprint.study_description_regex), re.IGNORECASE)
            if modality_re.search(incoming.Modality) and series_re.search(incoming.SeriesDescription) and \
                    study_re.search(incoming.StudyDescription) and sop_class_uid_re.search(incoming.SOPClassUID):
                to_return.append(fingerprint)

        return to_return

if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as d:
        fp = {"modality_regex": "MR",
              "sop_class_uid_regex": "",
              "study_description_regex": "HEST|Imp",
              "series_description_regex": "",
              "inference_server_url": "https://omen.onerm.dk/api/tasks/",
              "model_human_readable_id": "cns_t1_oars",
              "scus": [{"scu_ip": "127.0.0.1",
                   "scu_port": 11110,
                   "scu_ae_title": "DICOM_ENDPOINT_AE"}
              ]}

        with open(os.path.join(d, "fingerprint.json"), "w") as f:
            f.write(json.dumps(fp))
        db = DB(d)
        print(db.get_fingerprints())

        inc = Incoming(path="asdf",
                 last_timestamp=datetime.datetime.now(),
                 first_timestamp=datetime.datetime.now(),
                 PatientID="123123123",
                 StudyDescription="Neck Important neck",
                 SeriesDescription="This is an important series to perform",
                 SOPClassUID="1.2.840.10008.5.1.4.1.1.4",
                 Modality="MR")
        fp = db.get_fingerprint_from_incoming(incoming=inc)
        print(fp)
        assert fp