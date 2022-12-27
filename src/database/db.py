import os
import secrets
from typing import Union

import sqlalchemy
from sqlalchemy.orm import sessionmaker, scoped_session

from models.models import Incoming, Task, InferenceServerResponse, Destination


class DB:
    def __init__(self, data_dir, declarative_base):
        self.declarative_base = declarative_base
        self.data_dir = data_dir

        self.database_path = f'{self.data_dir}/database.db'
        self.database_url = f'sqlite:///{self.database_path}'

        self.engine = sqlalchemy.create_engine(self.database_url, future=True)

        # Check if database exists - if not, create scheme
        if not os.path.exists(self.database_path):
            self.declarative_base.metadata.create_all(self.engine)

        self.session_maker = sessionmaker(bind=self.engine)
        self.Session = scoped_session(self.session_maker)

    def upsert_incoming(self,
                        timestamp,
                        patient_id,
                        series_instance_uid,
                        modality,
                        study_description,
                        series_description,
                        sop_class_uid):

        path = os.path.join(self.data_dir, patient_id, series_instance_uid)
        # make dir for the incoming
        os.makedirs(path, exist_ok=True)

        with self.Session() as session:
            inc = session.query(Incoming).filter_by(PatientID=patient_id, SeriesInstanceUID=series_instance_uid).first()
            if inc:
                inc.last_timestamp = timestamp
                inc.is_idle = False
                session.commit()
                session.refresh(inc)
                return inc
            else:
                inc = Incoming(path=path,
                               last_timestamp=timestamp,
                               first_timestamp=timestamp,
                               PatientID=patient_id,
                               Modality=modality,
                               StudyDescription=study_description,
                               SeriesDescription=series_description,
                               SOPClassUID=sop_class_uid,
                               SeriesInstanceUID=series_instance_uid)
                return self.add_generic(inc)

    def get_incoming(self, id):
        with self.Session() as session:
            inc = session.query(Incoming).filter_by(id=id).first()
        return inc

    def get_incomings(self):
        with self.Session() as session:
            return list(session.query(Incoming))

    def get_incomings_by_kwargs(self, kwargs):
        with self.Session() as session:
            return list(session.query(Incoming).filter_by(**kwargs))

    def set_incoming_toggles(self,
                             incoming_id: str,
                             is_deleted: Union[bool, None] = None,
                             is_idle: Union[bool, None] = None):
        with self.Session() as session:
            inc = session.query(Incoming).filter_by(id=incoming_id).first()
            if is_deleted is not None:
                inc.is_deleted = is_deleted
            if is_idle is not None:
                inc.is_idle = is_idle

            session.commit()
            session.refresh(inc)
            return inc


    ####################### TASKS #######################
    def add_task(self,
                 incoming_id: int,
                 model_human_readable_id: str,
                 modality_regex: str,
                 sop_class_uid_regex: str,
                 series_description_regex: str,
                 study_description_regex: str,
                 exclude_regex: str,
                 inference_server_url: str):

        task = Task(incoming_id=incoming_id,
                    model_human_readable_id=model_human_readable_id,
                    modality_regex=modality_regex,
                    sop_class_uid_regex=sop_class_uid_regex,
                    series_description_regex=series_description_regex,
                    study_description_regex=study_description_regex,
                    exclude_regex=exclude_regex,
                    inference_server_url=inference_server_url)

        return self.add_generic(task)

    def get_task(self, id):
        with self.Session() as session:
            inc = session.query(Task).filter_by(id=id).first()
        return inc

    def get_tasks_by_kwargs(self, kwargs):
        with self.Session() as session:
            return list(session.query(Task).filter_by(**kwargs))

    def get_tasks(self):
        with self.Session() as session:
            return list(session.query(Task))

    def set_task_toggles(self,
                         task_id: str,
                         is_deleted: Union[bool, None] = None):
        with self.Session() as session:
            inc = session.query(Incoming).filter_by(id=task_id).first()
            if is_deleted is not None:
                inc.is_deleted = is_deleted

            session.commit()
            session.refresh(inc)
            return inc

    def set_task_status(self,
                        task_id: int,
                        status: int):
        with self.Session() as session:
            inc = session.query(Task).filter_by(id=task_id).first()
            inc.status = status

            session.commit()
            session.refresh(inc)
            return inc

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

    ################# INFERENCE SERVER RESPONSE #############
    def add_inference_server_response(self,
                                      task_id: int,
                                      uid: str,
                                      status_code: Union[int, None] = None):
        isr = InferenceServerResponse(task_id=task_id,
                                      uid=uid,
                                      status_code=status_code)
        return self.add_generic(isr)
    def set_inference_server_response_status_code(self,
                                 inference_server_response_id: str,
                                 status_code: int):
        with self.Session() as session:
            isr = session.query(InferenceServerResponse).filter_by(id=inference_server_response_id).first()
            isr.status_code = status_code
            session.commit()
            session.refresh(isr)
            return isr
    def add_generic(self, item):
        with self.Session() as session:
            session.add(item)
            session.commit()
            session.refresh(item)

        return item
