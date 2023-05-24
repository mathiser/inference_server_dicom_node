from typing import List, Union, Dict

from pydantic import BaseModel
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class SCU(BaseModel):
    scu_ip: str
    scu_port: int
    scu_ae_title: str

class Fingerprint(BaseModel):
    sub_fingerprints: List[Dict[str, str]]
    inference_server_url: str
    zip_path: str = "/"
    model_human_readable_id: str

    scus: Union[List[SCU], None] = None
class Fingerprint(Base):
    # Fingerprint regex
    __tablename__ = "fingerprint_matches"
    id = Column(Integer, index=True, unique=True, primary_key=True, autoincrement=True)
    created_timestamp = Column(DateTime, default=datetime.datetime.now)

    # Path identifier
    # Is the subpath in this the matching incoming will be put for the zip file to the inference server.
    zip_path = Column(String, default="/")

    # <./rand_string>
    file_path = Column(String, default=secrets.token_urlsafe)

    # Fingerprint regex
    modality_exp = Column(String, default="")
    sop_class_uid_exp = Column(String, default="")
    series_description_exp = Column(String, default="")
    study_description_exp = Column(String, default="")
    exclude_exp = Column(String, default="")
