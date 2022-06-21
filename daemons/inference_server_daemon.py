import json
import logging
import os
import tempfile
import threading
import zipfile
import time

import dotenv
import requests

from daemons.get_thread import GetJobThread

LOG_FORMAT = ('%(levelname)s:%(asctime)s:%(message)s')
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logging.info("Outside Main")

class InferenceServerDaemon(threading.Thread):
    def __init__(self,
                 scp,
                 inference_server_endpoint,
                 run_interval: int = 15,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scp = scp
        self.inference_server_endpoint = inference_server_endpoint
        self.queue_dict = self.scp.queue_dict
        self.previous_queue = None
        self.run_interval = run_interval
        self.threads = []

    def __del__(self):
        for t in self.threads:
            t.join()


    def run(self) -> None:
        while self.scp:
            time.sleep(self.run_interval)
            logging.info("Scanning for newcomers")
            self.previous_queue_dict = self.queue_dict.copy()

            to_remove = []
            for id, details in self.queue_dict.items():
                if details == self.previous_queue_dict[id]:
                    logging.info(f"Posting task {str(details)}")
                    res = self.post(path=details["path"],
                                    model_human_readable_id=details["model_human_readable_id"])
                    if res.ok:
                        to_remove.append(id)  # Pop from dict
                        uid = json.loads(res.content)
                        logging.info(f"Successful post of {details}.")
                        logging.info(f"UID: {uid}")
                        t = GetJobThread(uid=uid, inference_server_endpoint=self.inference_server_endpoint, timeout=300)
                        self.threads.append(t)
                        t.start()
                    else:
                        logging.info(f"Unsuccessful post: {res.content}")
                        continue



            for id in to_remove:
                del self.queue_dict[id]

    def post(self, path, model_human_readable_id):
        with tempfile.TemporaryFile() as tmp_file:
            with zipfile.ZipFile(tmp_file, "w") as zip_file:
                for fol, subs, files in os.walk(path):
                    for f in files:
                        zip_file.write(os.path.join(fol, f), arcname=f)
            tmp_file.seek(0)

            res = requests.post(self.inference_server_endpoint,
                                params={"model_human_readable_id": model_human_readable_id},
                                files={"zip_file": tmp_file},
                                verify="certs/cert.crt")
            return res
