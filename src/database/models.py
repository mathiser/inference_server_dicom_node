import datetime
from typing import Optional, List

from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import DeclarativeBase, relationship, mapped_column, Mapped


class Base(DeclarativeBase):
    pass


class DestinationFingerprintAssociation(Base):
    __tablename__ = "destination_fingerprint_associations"
    timestamp: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.now)

    destination_id: Mapped[int] = mapped_column(ForeignKey("destinations.id"), primary_key=True)
    fingerprint_id: Mapped[int] = mapped_column(ForeignKey("fingerprints.id"), primary_key=True)

    fingerprint: Mapped["Fingerprint"] = relationship(lazy="joined",
                                                      back_populates="destination_associations")

class TriggerFingerprintAssociation(Base):
    __tablename__ = "trigger_fingerprint_associations"
    timestamp: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.now)

    trigger_id: Mapped[int] = mapped_column(ForeignKey("triggers.id"), primary_key=True)
    fingerprint_id: Mapped[int] = mapped_column(ForeignKey("fingerprints.id"), primary_key=True)

    fingerprint: Mapped["Fingerprint"] = relationship(lazy="joined",
                                                      back_populates="trigger_associations")


######## Fingerprint Schemas ###########
class Trigger(Base):
    __tablename__ = "triggers"
    id: Mapped[int] = mapped_column(unique=True, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.now)

    # Regex matches
    study_description_pattern: Mapped[Optional[str]]
    series_description_pattern: Mapped[Optional[str]]
    sop_class_uid_exact: Mapped[Optional[str]]
    exclude_pattern: Mapped[Optional[str]]


class Destination(Base):
    __tablename__ = "destinations"
    id: Mapped[int] = mapped_column(unique=True, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.now)

    # The details of the receiver
    scu_ip: Mapped[str]
    scu_port: Mapped[int]
    scu_ae_title: Mapped[str]

class Fingerprint(Base):
    __tablename__ = "fingerprints"
    id: Mapped[int] = mapped_column(unique=True, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.now)

    version: Mapped[str] = mapped_column(default="1.0")
    description: Mapped[str] = mapped_column(default="")

    triggers: Mapped[List["Trigger"]] = relationship(lazy="joined",
                                                     secondary="trigger_fingerprint_associations",
                                                     viewonly=True)
    trigger_associations: Mapped[List[TriggerFingerprintAssociation]] = relationship(back_populates="fingerprint")

    # Inference Server
    inference_server_url: Mapped[str]
    human_readable_id: Mapped[str]

    destinations: Mapped[List["Destination"]] = relationship(lazy="joined",
                                                             secondary="destination_fingerprint_associations",
                                                             viewonly=True)
    destination_associations: Mapped[List[DestinationFingerprintAssociation]] = relationship(back_populates="fingerprint")
    delete_remotely: Mapped[bool] = mapped_column(default=True)
    delete_locally: Mapped[bool] = mapped_column(default=True)

########## Tasks ##########
class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(unique=True, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.now)

    fingerprint_id: Mapped[int] = mapped_column(ForeignKey("fingerprints.id"))
    fingerprint: Mapped["Fingerprint"] = relationship(lazy="joined", uselist=False)

    # tarped on pull from SCP. Ready to post.
    tar_path: Mapped[str]

    # Status stamp
    status: Mapped[int] = mapped_column(Integer, default=0)

    # Inference server uid
    inference_server_uid: Mapped[str] = mapped_column(nullable=True, default=None)
    inference_server_tar: Mapped[str] = mapped_column(nullable=True, default=None)

    # Toggles check for final deletes
    deleted_local: Mapped[bool] = mapped_column(default=False)
    deleted_remote: Mapped[bool] = mapped_column(default=False)