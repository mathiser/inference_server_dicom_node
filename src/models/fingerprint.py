from typing import Union, List

from pydantic import BaseModel


class Fingerprint(BaseModel):
    modality: str
    study_description_keywords: List[str]
    inference_server_url: str
    model_human_readable_id: str
    scu_ip: str
    scu_port: int
    scu_ae_title: str