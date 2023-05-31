import logging
from typing import Union
from urllib.parse import urljoin

import requests

from decorators.logging import log


class Client:
    def __init__(self, cert: Union[str, bool] = True, log_level=10):
        self.cert = cert

        LOG_FORMAT = ('%(levelname)s:%(asctime)s:%(message)s')
        logging.basicConfig(level=log_level, format=LOG_FORMAT)

    @log
    def post_task(self, task) -> requests.Response:
        url = urljoin(task.fingerprint.inference_server_url, "/api/tasks/")
        logging.debug(f"[ ] Posting task {task.__dict__} to {url}")
        with open(task.zip_path, "br") as zip_file:
            res = requests.post(url=url,
                                params={"model_human_readable_id": task.fingerprint.model_human_readable_id},
                                files={"zip_file": zip_file},
                                verify=self.cert)
            assert isinstance(res, requests.Response)
            logging.debug(f"[X] Posting task {task.__dict__} to {url}")

        return res
    @log

    def get_task(self, task) -> requests.Response:
        url = urljoin(task.fingerprint.inference_server_url, "/api/tasks/")
        logging.debug(f"[ ] Getting task {task.inference_server_uid} from {url}")

        res = requests.get(url=urljoin(url, task.inference_server_uid),
                           verify=self.cert)
        logging.debug(f"[X] Getting task {task.inference_server_uid} from {url}")

        return res
    @log
    def delete_task(self, task) -> requests.Response:
        url = urljoin(task.fingerprint.inference_server_url, "/api/tasks/")
        logging.debug(f"[ ] Deleting task {task.inference_server_uid} from {url}")

        res = requests.delete(url=urljoin(urljoin(task.fingerprint.inference_server_url, "/api/tasks/"), task.inference_server_uid),
                              verify=self.cert)
        return res


