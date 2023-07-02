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
        task.inference_server_uid = uid
        self.tasks[uid] = task
        res_t = {"uid": uid,
                           "inference_server_tar": task.inference_server_tar,
                           "tar_path": task.tar_path}
        
        res = requests.Response()
        if success:
            res.status_code = 200
            res._content = json.dumps(res_t)
        else:
            res.status_code = 500
            res._content = json.dumps(res_t)

        return res


    def get_task(self, task, error_code=False) -> requests.Response:
        res = requests.Response()
        if error_code:
            res.status_code = error_code
            res._content = json.dumps('There is a little black spot on the sun to day')
        else:
            t = self.tasks[task.inference_server_uid]
            print(t)
            print(f"HERE: {t}")
            res.status_code = 200
            with open(t.tar_path, "br") as r:
                res._content = r.read()
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


