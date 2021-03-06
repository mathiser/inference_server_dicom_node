from typing import List

from pydantic import BaseModel


class SCU(BaseModel):
    scu_ip: str
    scu_port: int
    scu_ae_title: str


class Fingerprint(BaseModel):
    modality_regex: str = ""
    sop_class_uid_regex: str = ""
    series_description_regex: str = ""
    study_description_regex: str = ""
    exclude_regex: str = "a^"
    inference_server_url: str
    model_human_readable_id: str
    scus: List[SCU]
