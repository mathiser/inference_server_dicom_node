import logging
import tempfile
from typing import Any, Union, List

import uvicorn
from fastapi import FastAPI

from database.db import DB
from database.models import Trigger, Destination

class DicomNodeAPI(FastAPI):
    def __init__(self, db: DB, log_level, **extra: Any):
        super().__init__(db=db, **extra)
        self.db = db

        LOG_FORMAT = ('%(levelname)s:%(asctime)s:%(message)s')
        logging.basicConfig(level=log_level, format=LOG_FORMAT)

        @self.get("/")
        def public_hello_world():
            return {"message": "Hello world - Welcome to Inference Server Dicom Node"}

        @self.post("/fingerprints/")
        def add_fingerprint(inference_server_url: str,
                            human_readable_id: str,
                            version: Union[str, None] = None,
                            description: Union[str, None] = None,
                            delete_locally: Union[bool, None] = None,
                            delete_remotely: Union[bool, None] = None,
                            ):
            return self.db.add_fingerprint(version=version,
                                           description=description,
                                           inference_server_url=inference_server_url,
                                           human_readable_id=human_readable_id,
                                           delete_remotely=delete_remotely,
                                           delete_locally=delete_locally)

        @self.post("/destination_fingerprint_association/")
        def add_destination_fingerprint_association(fingerprint_id: int,
                                                    destination_id: int):
            return self.db.add_destination_to_fingerprint(fingerprint_id=fingerprint_id,
                                                          destination_id=destination_id)

        @self.get("/fingerprints/")
        def get_fingerprints():
            return list(self.db.get_fingerprints())

        @self.get("/triggers/")
        def get_triggers():
            return list(self.db.generic_get_all(Trigger))

        @self.get("/destinations/")
        def get_destinations():
            return list(self.db.generic_get_all(Destination))

        @self.post("/triggers/")
        def add_trigger(fingerprint_id: Union[int, None] = None,
                        study_description_pattern: Union[str, None] = None,
                        series_description_pattern: Union[str, None] = None,
                        sop_class_uid_exact: Union[str, None] = None,
                        exclude_pattern: Union[str, None] = None):
            return self.db.add_trigger(fingerprint_id=fingerprint_id,
                                       study_description_pattern=study_description_pattern,
                                       series_description_pattern=series_description_pattern,
                                       sop_class_uid_exact=sop_class_uid_exact,
                                       exclude_pattern=exclude_pattern)

        @self.post("/destinations/")
        def add_destinations(scu_ip: str,
                                 scu_port: int,
                                 scu_ae_title: str,
                                 fingerprint_id: Union[int, None] = None,):
                                 
            return self.db.add_destination(scu_ip=scu_ip,
                                           scu_port=scu_port,
                                           scu_ae_title=scu_ae_title,
                                           fingerprint_id=fingerprint_id)


        @self.delete("/triggers/{trigger_id}")
        def delete_trigger(trigger_id: int):
            return self.db.delete_trigger(trigger_id=trigger_id)

        @self.delete("/destinations/{destination_id}")
        def delete_destination(destination_id: int):
            return self.db.delete_destination(destination_id=destination_id)

        @self.delete("/fingerprints/{fingerprint_id}")
        def delete_destination(fingerprint_id: int):
            return self.db.delete_fingerprint(fingerprint_id=fingerprint_id)



if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp_dir:
        db = DB(base_dir=tmp_dir)
        app = DicomNodeAPI(db=db)
        uvicorn.run(app=app,
                    host="localhost",
                    port=8128)
