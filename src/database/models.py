from typing import Union

from pydantic import BaseModel


class DCMNodeEndpoint(BaseModel):
    scp_ip: str
    scp_port: int
    scp_ae_title: str
    scp_storage_dir: Union[str, None]
    inference_server_url: str
    model_human_readable_id: str
    scu_ip: str
    scu_port: int
    scu_ae_title: str