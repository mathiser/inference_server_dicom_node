import datetime
import secrets
import tempfile

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

######## Fingerprint Schemas ###########
class Trigger(Base):
    __tablename__ = "triggers"
    id = Column(Integer, unique=True, primary_key=True, autoincrement=True)
    fingerprint_id = Column(Integer, ForeignKey("fingerprints.id"))

    # Regex matches
    study_description_regex = Column(String)
    series_description_regex = Column(String)
    sop_class_uid_regex = Column(String)
class Destination(Base):
    __tablename__ = "destinations"
    id = Column(Integer, unique=True, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.datetime.now)
    fingerprint_id = Column(Integer, ForeignKey("fingerprints.id"))

    # The details of the receiver
    scu_ip = Column(String)
    scu_port = Column(Integer)
    scu_ae_title = Column(String)

class InferenceServer(Base):
    __tablename__ = "inference_servers"
    id = Column(Integer, unique=True, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.datetime.now)
    fingerprint_id = Column(Integer, ForeignKey("fingerprints.id"))

    # Inference Server Details
    model_human_readable_id = Column(String)
    inference_server_url = Column(String)

class Fingerprint(Base):
    __tablename__ = "fingerprints"
    id = Column(Integer, unique=True, primary_key=True, autoincrement=True)

    triggers = relationship("Trigger", lazy="joined")
    inference_server = relationship("InferenceServer", lazy="joined", uselist=False)
    destinations = relationship("Destination", lazy="joined")


########## Relates to incomings ##########
class Incoming(Base):
    __tablename__ = "incomings"
    id = Column(Integer, index=True, unique=True, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.datetime.now)

    # Patient infomation
    patient_id = Column(String)

    # zipped on pull from SCP. Ready to post.
    zip_path = Column(String)

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, index=True, unique=True, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.datetime.now)

    fingerprint_id = Column(Integer, ForeignKey("fingerprints.id"))
    fingerprint = relationship("Fingerprint", lazy="joined", uselist=False)

    incoming_id = Column(Integer, ForeignKey("incomings.id"))
    incoming = relationship("Incoming", lazy=True)

    # Status stamp
    status = Column(Integer, default=0)

    # Inference server uid
    inference_server_uid = Column(String, nullable=True, default=None)

    # Toggles check for final deletes
    deleted_local = Column(Boolean, default=False)
    deleted_remote = Column(Boolean, default=False)





