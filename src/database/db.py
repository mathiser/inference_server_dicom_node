import os
import shutil
import warnings
from typing import Union

import sqlalchemy
from sqlalchemy.orm import sessionmaker, scoped_session

from models.models import Incoming, Task, InferenceServerResponse, Destination, FingerprintMatch, InferenceServerTask, \
    TaskStatus


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

        self.session_maker = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.Session = scoped_session(self.session_maker)

    def burst_insert_incoming(self,
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

    def get_incoming_by_fingerprint(self,
                                    patient_id,
                                    modality_exp="",
                                    sop_class_uid_exp="",
                                    series_description_exp="",
                                    study_description_exp="",
                                    exclude_exp=""):
        with self.Session() as session:
            # Filter by patient
            pid_incs = session.query(Incoming).filter(patient_id == Incoming.PatientID)

            # Filter by triggers
            incs = pid_incs.filter(Incoming.Modality.contains(modality_exp),
                                   Incoming.SOPClassUID.contains(sop_class_uid_exp),
                                   Incoming.SeriesDescription.contains(series_description_exp),
                                   Incoming.StudyDescription.contains(study_description_exp))

            # Filter by exclusion trigger if it is set
            if not len(exclude_exp) == 0:
                incs = incs.filter(~Incoming.Modality.contains(exclude_exp),
                                   ~Incoming.SOPClassUID.contains(exclude_exp),
                                   ~Incoming.SeriesDescription.contains(exclude_exp),
                                   ~Incoming.StudyDescription.contains(exclude_exp))
            if incs.count() > 1:
                warnings.warn(f"More than one matching incoming is found. Using the first, which is {incs.first()}",
                              UserWarning)
        return incs.first()

    def get_incomings_by_kwargs(self, kwargs):
        with self.Session() as session:
            return list(session.query(Incoming).filter_by(**kwargs))

    def update_incoming(self,
                        incoming_id: int,
                        is_deleted: Union[bool, None] = None,
                        is_idle: Union[bool, None] = None):
        with self.Session() as session:
            inc = session.query(Incoming).filter_by(id=incoming_id).first()
            if is_deleted:
                try:
                    shutil.rmtree(path=inc.path)
                    inc.is_deleted = is_deleted
                except FileNotFoundError:
                    inc.is_deleted = is_deleted
                except Exception as e:
                    raise e

            if is_idle is not None:
                inc.is_idle = is_idle

            session.commit()
            session.refresh(inc)
            return inc

    ####################### TASKS #######################
    def add_task(self,
                 model_human_readable_id: str,
                 inference_server_url: str):

        task = Task(model_human_readable_id=model_human_readable_id,
                    inference_server_url=inference_server_url)

        task = self.add_generic(task)
        self.add_task_status(task_id=task.id, status=0)

        return self.get_task(task.id)

    def get_task(self, id):
        with self.Session() as session:
            inc = session.query(Task).filter_by(id=id).first()
        return inc

    def get_tasks_by_kwargs(self, kwargs):
        with self.Session() as session:
            return list(session.query(Task).filter_by(**kwargs))

    def get_tasks_by_status(self, status):
        to_return = []
        with self.Session() as session:
            tasks = list(session.query(Task))
            for task in tasks:
                if task.status == status:
                    to_return.append(task)
        return to_return

    def get_tasks(self):
        with self.Session() as session:
            return list(session.query(Task))

    def update_task(self,
                    task_id: int,
                    is_deleted: Union[bool, None] = None,
                    status: Union[int, None] = None):
        if status:
            self.add_task_status(task_id=task_id, status=status)
if
        if is_deleted:
            with self.Session() as session:
                t = session.query(Task).filter_by(id=task_id).first()
                t.is_deleted = is_deleted

                session.commit()
                session.refresh(t)

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

    ################# INFERENCE SERVER RESPONSE #############
    def add_inference_server_response(self,
                                      task_id: int,
                                      status_code: int):
        isr = InferenceServerResponse(task_id=task_id,
                                      status_code=status_code)
        return self.add_generic(isr)

    ################# INFERENCE SERVER TASK #############
    def add_inference_server_task(self,
                                 task_id: int,
                                 uid: str):
        isr = InferenceServerTask(task_id=task_id,
                                 uid=uid)
        return self.add_generic(isr)

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
