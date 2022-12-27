import json
import os
import os
import random
import secrets
import shutil
import tempfile
import zipfile
from io import BytesIO
from typing import Union, BinaryIO
from urllib.parse import urljoin

import requests


class MockClient:
    def __init__(self, cert: Union[str, bool] = True):
        self.tasks = {}

    def post_task(self, task, success=True) -> requests.Response:
        uid = secrets.token_urlsafe()
        self.tasks[uid] = task
        res = requests.Response()
        if success:
            res.status_code = 200
            res._content = json.dumps(uid)
        else:
            res.status_code = 500
            res._content = json.dumps(uid)

        return res


    def get_task(self, task, error_code=False) -> requests.Response:
        res = requests.Response()
        if error_code:
            res.status_code = error_code
            res._content = json.dumps('There is a little black spot on the sun to day')
        else:
            try:
                t = self.tasks[task.inference_server_response.uid]
                res.status_code = 200
                shutil.make_archive("tmp", "zip", root_dir="dicom_networking/tests/test_image/case2a/")
                with open("tmp.zip", "br") as r:
                    res._content = r.read()
                shutil.rmtree("tmp.zip")

            except Exception as e:
                res.status_code = 554
                res._content = json.dumps("Task not found")

        return res

    def delete_task(self, task) -> requests.Response:
        try:
            del self.tasks[task.inference_server_response.uid]
            res = requests.Response()
            res.status_code = 200
            res._content = json.dumps('Task successfully deleted')
        except Exception as e:
            res = requests.Response()
            res.status_code = 500
            res._content = json.dumps(e)
        return res


