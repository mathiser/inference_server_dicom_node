import json
import secrets
import shutil
from typing import Union

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
                t = self.tasks[task.inference_server_uid]
                res.status_code = 200
                with open(t.zip_path, "br") as r:
                    res._content = r.read()

            except Exception as e:
                res.status_code = 554
                res._content = json.dumps("Task not found")

        return res

    def delete_task(self, task) -> requests.Response:
        try:
            del self.tasks[task.inference_server_uid]
            res = requests.Response()
            res.status_code = 200
            res._content = json.dumps('Task successfully deleted')
        except Exception as e:
            res = requests.Response()
            res.status_code = 500
            res._content = json.dumps(e)
        return res


