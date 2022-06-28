import json
import logging
import os

from database.models import DCMNodeEndpoint


class DB:
    def __init__(self, endpoint_dir):
        self.endpoint_dir = endpoint_dir
        self.dicom_endpoints = []
        for fol, subs, files in os.walk(endpoint_dir):
            for file in files:
                if file.endswith(".json"):
                    file_path = os.path.join(fol, file)
                    try:
                        with open(file_path, "r") as r:
                            self.dicom_endpoints.append(DCMNodeEndpoint(**json.loads(r.read())))

                    except Exception as e:
                        logging.error(e)
        if len(self.dicom_endpoints) == 0:
            logging.info("No dicom endpoints found")

    def get_endpoints(self):
        return self.dicom_endpoints
