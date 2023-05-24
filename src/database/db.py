import os
import secrets
from typing import Union

import sqlalchemy
from sqlalchemy.orm import sessionmaker, scoped_session, Query

from database.models import Incoming, Destination, Fingerprint, Trigger, InferenceServer, Task
from database.models import Base


class DB:
    def __init__(self, data_dir):
        self.data_dir = data_dir

        self.database_path = f'{self.data_dir}/database.db'
        self.database_url = f'sqlite:///{self.database_path}'

        self.engine = sqlalchemy.create_engine(self.database_url, future=True)

        # Check if database exists - if not, create scheme
        if not os.path.exists(self.database_path):
            Base.metadata.create_all(self.engine)

        self.session_maker = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.Session = scoped_session(self.session_maker)

    ################### Fingerprinting ##################
    def add_fingerprint(self) -> Fingerprint:
        fpm = Fingerprint()
        return self.generic_add(fpm)

    def get_fingerprint(self, id) -> Fingerprint:
        with self.Session() as session:
            inc = session.query(Fingerprint).filter_by(id=id).first()
        return inc

    def add_trigger(self,
                    fingerprint_id: int,
                    study_description_regex: str,
                    series_description_regex: str,
                    sop_class_uid_regex: str) -> Trigger:

        trigger = Trigger(fingerprint_id=fingerprint_id,
                          study_description_regex=study_description_regex,
                          series_description_regex=series_description_regex,
                          sop_class_uid_regex=sop_class_uid_regex)
        return self.generic_add(trigger)

    def add_destination(self,
                        fingerprint_id: int,
                        scu_ip: str,
                        scu_port: int,
                        scu_ae_title: str) -> Destination:
        dest = Destination(fingerprint_id=fingerprint_id,
                           scu_ip=scu_ip,
                           scu_port=scu_port,
                           scu_ae_title=scu_ae_title)
        return self.generic_add(dest)

    def add_inference_server(self,
                             fingerprint_id: int,
                             model_human_readable_id: str,
                             inference_server_url: str) -> InferenceServer:
        inference_server = InferenceServer(fingerprint_id=fingerprint_id,
                                           inference_server_url=inference_server_url,
                                           model_human_readable_id=model_human_readable_id)
        return self.generic_add(inference_server)

    ##### DYNAMIC #####
    def add_incoming(self,
                     patient_id,
                     zip_path) -> Incoming:
        # Add to DB
        incoming = Incoming(patient_id=patient_id,
                            zip_path=zip_path)
        return self.generic_add(incoming)

    def get_incoming(self, id) -> Incoming:
        with self.Session() as session:
            inc = session.query(Incoming).filter_by(id=id).first()
        return inc

    def get_incomings(self) -> Query:
        with self.Session() as session:
            return session.query(Incoming)

    def get_incomings_by_kwargs(self, kwargs) -> Query:
        with self.Session() as session:
            return session.query(Incoming).filter_by(**kwargs)

    def add_task(self,
                 fingerprint_id,
                 incoming_id) -> Task:
        task = Task(fingerprint_id=fingerprint_id,
                    incoming_id=incoming_id)
        return self.generic_add(task)

    def get_tasks_by_kwargs(self, kwargs) -> Query:
        with self.Session() as session:
            return session.query(Task).filter_by(**kwargs)

    def get_tasks(self) -> Query:
        with self.Session() as session:
            return session.query(Task)

    def update_task(self,
                    task_id: int,
                    inference_server_uid: Union[str, None] = None,
                    deleted_local: Union[bool, None] = None,
                    deleted_remote: Union[bool, None] = None,
                    status: Union[int, None] = None) -> Task:
        with self.Session() as session:
            t = session.query(Task).filter_by(id=task_id).first()
            if inference_server_uid:
                t.inference_server_uid = inference_server_uid
            if deleted_local:
                t.deleted_local = deleted_local
            if deleted_remote:
                t.deleted_remote = deleted_remote
            if status:
                t.status = status

            session.commit()
            session.refresh(t)

    def generic_add(self, item):
        with self.Session() as session:
            session.add(item)
            session.commit()
            session.refresh(item)

        return item
