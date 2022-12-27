import datetime

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Incoming(Base):
    __tablename__ = "incomings"
    id = Column(Integer, index=True, unique=True, primary_key=True, autoincrement=True)
    last_timestamp = Column(DateTime, default=datetime.datetime.now)
    first_timestamp = Column(DateTime, default=datetime.datetime.now)
    path = Column(String)
    PatientID = Column(String)
    StudyDescription = Column(String)
    SeriesDescription = Column(String)
    SeriesInstanceUID = Column(String)
    Modality = Column(String)
    SOPClassUID = Column(String)
    is_deleted = Column(Boolean, default=False)
    is_idle = Column(Boolean, default=False)

class Destination(Base):
    __tablename__ = "destinations"
    id = Column(Integer, unique=True, primary_key=True, autoincrement=True)

    # The task this destination belongs to
    task_id = Column(Integer, ForeignKey("tasks.id"))

    # The details of the receiver
    scu_ip = Column(String)
    scu_port = Column(Integer)
    scu_ae_title = Column(String)

class InferenceServerResponse(Base):
    __tablename__ = "inference_server_responses"
    id = Column(Integer, unique=True, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    uid = Column(String)
    status_code = Column(Integer, nullable=True)   # 500: Internal server error,
                                                    # 551: Task pending
                                                    # 552: Task failed
                                                    # 553: Task finished, but output zip not found.
                                                    # 554: Not found
class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, index=True, unique=True, primary_key=True, autoincrement=True)

    # Incoming details
    incoming_id = Column(Integer, ForeignKey("incomings.id"))
    incoming = relationship("Incoming", lazy="joined")

    # Fingerprint regex
    modality_regex = Column(String, default="")
    sop_class_uid_regex = Column(String, default="")
    series_description_regex = Column(String, default="")
    study_description_regex = Column(String, default="")
    exclude_regex = Column(String, default="a^")

    # Inference Server Details
    model_human_readable_id = Column(String)
    inference_server_url = Column(String)

    # Status
    # 0: pending,
    # 1: fingerprinted,
    # 2: posted to inference server,
    # 3: received response from server
    # 100: posted to all destinations and finished
    status = Column(Integer, default=0)
    is_deleted = Column(Boolean, default=False)

    # SCU details
    destinations = relationship("Destination", lazy="joined")
    inference_server_response = relationship("InferenceServerResponse", lazy="joined", uselist=False)


