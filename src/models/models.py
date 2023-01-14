import datetime
import tempfile

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Incoming(Base):
    __tablename__ = "incomings"
    id = Column(Integer, index=True, unique=True, primary_key=True, autoincrement=True)
    last_timestamp = Column(DateTime, default=datetime.datetime.now)
    first_timestamp = Column(DateTime, default=datetime.datetime.now)

    # Patient infomation
    PatientID = Column(String)
    SeriesInstanceUID = Column(String)
    StudyDescription = Column(String)
    SeriesDescription = Column(String)
    Modality = Column(String)
    SOPClassUID = Column(String)

    # /<PatientID>/<SeriesInstanceUID>
    path = Column(String)

    # Toggles used for queries
    is_deleted = Column(Boolean, default=False)
    is_idle = Column(Boolean, default=False)

    # #
    # fingerprint_matches = relationship("FingerprintMatch",
    #                                     lazy="joined",
    #                                     back_populates="incoming")


class FingerprintMatch(Base):
    # Fingerprint regex
    __tablename__ = "fingerprint_matches"
    id = Column(Integer, index=True, unique=True, primary_key=True, autoincrement=True)
    created_timestamp = Column(DateTime, default=datetime.datetime.now)

    # Path identifier
    # Is the subpath in this the matching incoming will be put for the zip file to the inference server.
    zip_path = Column(String, default="/")

    # Incoming
    incoming_id = Column(Integer, ForeignKey("incomings.id"))
    incoming = relationship("Incoming", lazy="select", uselist=False)

    # Task details
    task_id = Column(Integer, ForeignKey("tasks.id"))
    task = relationship("Task", lazy="joined", uselist=False, back_populates="fingerprint_matches")

    # Fingerprint regex
    modality_exp = Column(String, default="")
    sop_class_uid_exp = Column(String, default="")
    series_description_exp = Column(String, default="")
    study_description_exp = Column(String, default="")
    exclude_exp = Column(String, default="")


class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, index=True, unique=True, primary_key=True, autoincrement=True)

    # Status stamps
    _statuses = relationship("TaskStatus", lazy="joined")

    # Inference Server Details
    model_human_readable_id = Column(String)
    inference_server_url = Column(String)
    path = Column(String, default=tempfile.mkdtemp)

    # FingerprintMatches
    fingerprint_matches = relationship("FingerprintMatch", lazy="joined", back_populates="task")

    # SCU details
    destinations = relationship("Destination", lazy="joined")

    # Inference server uid
    inference_server_task = relationship("InferenceServerTask", lazy="joined", uselist=False)

    # response details
    _inference_server_responses = relationship("InferenceServerResponse", lazy="joined")

    @property
    def status(self):
        print(self._statuses[-1].status)
        return self._statuses[-1].status

    @property
    def inference_server_response(self):
        return self._inference_server_responses[-1]


class Destination(Base):
    __tablename__ = "destinations"
    id = Column(Integer, unique=True, primary_key=True, autoincrement=True)
    created_timestamp = Column(DateTime, default=datetime.datetime.now)

    # The task this destination belongs to
    task_id = Column(Integer, ForeignKey("tasks.id"))

    # The details of the receiver
    scu_ip = Column(String)
    scu_port = Column(Integer)
    scu_ae_title = Column(String)

    is_sent = Column(Boolean, default=False)


class InferenceServerTask(Base):
    __tablename__ = "inference_server_tasks"
    id = Column(Integer, index=True, unique=True, primary_key=True, autoincrement=True)
    created_timestamp = Column(DateTime, default=datetime.datetime.now)

    # Task details
    task_id = Column(Integer, ForeignKey("tasks.id"))

    # The uid
    uid = Column(String)



class InferenceServerResponse(Base):
    __tablename__ = "inference_server_responses"
    id = Column(Integer, unique=True, primary_key=True, autoincrement=True)
    created_timestamp = Column(DateTime, default=datetime.datetime.now)

    task_id = Column(Integer, ForeignKey("tasks.id"))

    # 500: Internal server error,
    # 551: Task pending
    # 552: Task failed
    # 553: Task finished, but output zip not found.
    # 554: Not found
    status_code = Column(Integer, nullable=True)


class TaskStatus(Base):
    __tablename__ = "task_statuses"
    id = Column(Integer, index=True, unique=True, primary_key=True, autoincrement=True)
    created_timestamp = Column(DateTime, default=datetime.datetime.now)

    # Task details
    # 0 is pending
    # 1 is fingerprinted
    # 2 is ready to send to inference server
    task_id = Column(Integer, ForeignKey("tasks.id"))

    # The uid
    status = Column(Integer)
