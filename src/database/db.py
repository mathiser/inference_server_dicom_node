import json
import logging
import os
import tempfile
from typing import List
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from models import Fingerprint, Incoming


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
                            self.fingerprints.append(Fingerprint(**json.loads(r.read())))

                    except Exception as e:
                        logging.error(e)
        if len(self.fingerprints) == 0:
            logging.info("No fingerprints found")

    def get_fingerprints(self):
        return self.fingerprints

    def get_fingerprint_from_incoming(self, incoming: Incoming) -> List[Fingerprint]:
        for fingerprint in self.fingerprints:
            if fingerprint.modality == incoming.Modality or fingerprint.modality == "*":
                for kw in fingerprint.study_description_keywords:
                    if kw in incoming.StudyDescription or kw == "*":
                        yield fingerprint
                        break  # Breaking keyword loop


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as d:
        fp = {"modality": "CT",
              "study_description_keywords": ["HN", "CNS", "HEST"],
              "inference_server_url": "https://some-inferenceserver/api/tasks/",
              "model_human_readable_id": "hello-world",
              "scu_ip": "127.0.0.1",
              "scu_port": "11110",
              "scu_ae_title": "PACS_TITLE"
              }
        with open(os.path.join(d, "fingerprint.json"), "w") as f:
            f.write(json.dumps(fp))
        db = DB(d)
        print(db.get_fingerprints())
