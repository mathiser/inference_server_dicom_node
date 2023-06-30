import os
import secrets
from typing import Union, List

import sqlalchemy
from sqlalchemy.orm import sessionmaker, scoped_session, Query

from database.models import Destination, Fingerprint, Trigger, Task, \
    DestinationFingerprintAssociation
from database.models import Base


class DB:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.data_dir = os.path.join(self.base_dir, "data")
        self.db_dir = os.path.join(self.base_dir, "db")

        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.db_dir, exist_ok=True)

        self.database_path = f'{self.db_dir}/database.db'
        self.database_url = f'sqlite:///{self.database_path}'

        self.engine = sqlalchemy.create_engine(self.database_url, future=True)

        # Check if database exists - if not, create scheme
        if not os.path.isfile(self.database_path):
            Base.metadata.create_all(self.engine)

        self.session_maker = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.Session = scoped_session(self.session_maker)

    def generate_storage_folder(self):
        path = os.path.join(self.data_dir, secrets.token_urlsafe(8))
        os.makedirs(path)
        return path

    def add_destination_to_fingerprint(self, fingerprint_id, destination_id):
        ass = self.generic_add(DestinationFingerprintAssociation(fingerprint_id=fingerprint_id,
                                                                 destination_id=destination_id))
        return ass

    ################### Fingerprinting ##################
    def add_fingerprint(self,
                        human_readable_id: str,
                        inference_server_url: str,
                        version: Union[str, None] = None,
                        description: Union[str, None] = None,
                        destination_ids: List[int] = [],
                        delete_locally: Union[bool, None] = None,
                        delete_remotely: Union[bool, None] = None,
                        ) -> Fingerprint:
        fp = Fingerprint(version=version,
                         description=description,
                         human_readable_id=human_readable_id,
                         inference_server_url=inference_server_url,
                         delete_remotely=delete_remotely,
                         delete_locally=delete_locally)
        fp = self.generic_add(fp)

        if destination_ids:
            for dest_id in destination_ids:
                self.add_destination_to_fingerprint(fp.id, dest_id)

        return self.get_fingerprint(fp.id)

    def get_fingerprint(self, id) -> Fingerprint:
        with self.Session() as session:
            inc = session.query(Fingerprint).filter_by(id=id).first()
        return inc

    def get_fingerprints(self) -> Query:
        with self.Session() as session:
            return session.query(Fingerprint)

    def add_trigger(self,
                    fingerprint_id: int,
                    study_description_pattern: Union[str, None] = None,
                    series_description_pattern: Union[str, None] = None,
                    sop_class_uid_exact: Union[str, None] = None,
                    exclude_pattern: Union[str, None] = None) -> Trigger:

        trigger = Trigger(fingerprint_id=fingerprint_id,
                          study_description_pattern=study_description_pattern,
                          series_description_pattern=series_description_pattern,
                          sop_class_uid_exact=sop_class_uid_exact,
                          exclude_pattern=exclude_pattern)
        return self.generic_add(trigger)

    def add_destination(self,
                        scu_ip: str,
                        scu_port: int,
                        scu_ae_title: str) -> Destination:
        dest = Destination(scu_ip=scu_ip,
                           scu_port=scu_port,
                           scu_ae_title=scu_ae_title)
        return self.generic_add(dest)

    ##### DYNAMIC #####
    def add_task(self,
                 fingerprint_id) -> Task:
        storage_fol = self.generate_storage_folder()
        task = Task(fingerprint_id=fingerprint_id,
                    tar_path=os.path.join(storage_fol, "input.tar.gz"),
                    inference_server_tar=os.path.join(storage_fol, "output.tar.gz"))
        return self.generic_add(task)

    def get_tasks_by_kwargs(self, kwargs) -> Query:
        with self.Session() as session:
            return session.query(Task).filter_by(**kwargs)

    def get_tasks(self) -> Query:
        return self.generic_get_all(Task)

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
            return t

    def generic_add(self, item):
        with self.Session() as session:
            session.add(item)
            session.commit()
            session.refresh(item)

        return item

    def generic_get(self, cls, id):
        with self.Session() as session:
            return session.query(cls).filter_by(id=id).first()

    def generic_get_all(self, cls):
        with self.Session() as session:
            return session.query(cls)

    def generic_delete(self, cls, id):
        with self.Session() as session:
            try:
                deleted_rows = session.query(cls).filter_by(id=id).delete()
                session.commit()
                return deleted_rows
            except Exception as e:
                print(e)
                return False

    def delete_destination(self, destination_id):
        try:
            return self.generic_delete(Destination, destination_id)

        except:
            return False

    def delete_trigger(self, trigger_id):
        try:
            return self.generic_delete(Trigger, trigger_id)
        except:
            return False


    def delete_fingerprint(self, fingerprint_id):
        try:
            # Cannot get cascades to work. Doing the work for sqlalchemy. Fix at some point.
            fp = self.get_fingerprint(fingerprint_id)

            # Delete triggers
            for t in fp.triggers:
                self.generic_delete(Trigger, t.id)

            with self.Session() as session:
                try:
                    deleted_rows = session.query(DestinationFingerprintAssociation).filter_by(fingerprint_id=fp.id).delete()
                    session.commit()
                except Exception as e:
                    print(e)

            return self.generic_delete(Fingerprint, fingerprint_id)
        except Exception as e:
            print(e)
            raise e
