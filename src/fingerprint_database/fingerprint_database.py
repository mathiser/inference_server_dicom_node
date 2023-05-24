import json
import logging
import os

from fingerprint_database.models import Fingerprint
import os
import shutil
import warnings
from typing import Union

import sqlalchemy
from sqlalchemy.orm import sessionmaker, scoped_session
from fingerprint_database.models import Base


class FingerprintDatabase:
    def __init__(self, fingerprint_dir):
        self.fingerprint_dir = fingerprint_dir

        self.database_url = 'sqlite://'
        self.engine = sqlalchemy.create_engine(self.database_url, future=True)

        Base.metadata.create_all(self.engine)
        self.session_maker = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.Session = scoped_session(self.session_maker)

        # Load fingerprints from conf files
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


    ################### DESTINATIONS ##################
    def add_destination(self,
                        task_id: int,
                        scu_ip: str,
                        scu_port: int,
                        scu_ae_title: str):
        dest = Destination(task_id=task_id,
                           scu_ip=scu_ip,
                           scu_port=scu_port,
                           scu_ae_title=scu_ae_title)
        return self.add_generic(dest)

    def update_destination(self,
                           destination_id: int,
                           is_sent: Union[bool, None] = None):
        with self.Session() as session:
            dest = session.query(Destination).filter_by(id=destination_id).first()

            if is_sent is not None:
                dest.is_sent = is_sent

            session.commit()
            session.refresh(dest)
            return dest

    ################## FINGERPRINTMATCH #################
    def add_fingerprint_match(self,
                              task_id: int,
                              incoming_id: int,
                              zip_path: str,
                              modality_exp: str,
                              sop_class_uid_exp: str,
                              series_description_exp: str,
                              study_description_exp: str,
                              exclude_exp):

        fpm = FingerprintMatch(task_id=task_id,
                               zip_path=zip_path,
                               modality_exp=modality_exp,
                               sop_class_uid_exp=sop_class_uid_exp,
                               exclude_exp=exclude_exp,
                               incoming_id=incoming_id,
                               study_description_exp=study_description_exp,
                               series_description_exp=series_description_exp)

        return self.add_generic(fpm)

    ################# INFERENCE SERVER UID #############
    def add_task_status(self,
                        task_id: int,
                        status: int):
        ts = TaskStatus(task_id=task_id,
                        status=status)
        return self.add_generic(ts)

    def add_generic(self, item):
        with self.Session() as session:
            session.add(item)
            session.commit()
            session.refresh(item)

        return item
