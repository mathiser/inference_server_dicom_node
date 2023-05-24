import os
import tempfile
import zipfile
from typing import Union
from urllib.parse import urljoin

import requests


class Client:
    def __init__(self, cert: Union[str, bool] = True):
        self.cert = cert

    def post_task(self, task) -> requests.Response:
        with open(task.zip_path, "br") as zip_file:
            res = requests.post(url=task.inference_server_url,
                                params={"model_human_readable_id": task.model_human_readable_id},
                                files={"zip_file": zip_file},
                                verify=self.cert)
            return res

    def get_task(self, task) -> requests.Response:
        res = requests.get(url=urljoin(task.inference_server_url, task.inference_server_response.uid),
                           verify=self.cert)
        return res

    def delete_task(self, task) -> requests.Response:
        res = requests.delete(url=urljoin(task.inference_server_url, task.inference_server_response.uid),
                              verify=self.cert)
        return res


