from typing import List, Union, Dict

from pydantic import BaseModel


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
