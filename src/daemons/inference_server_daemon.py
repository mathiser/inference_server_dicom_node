import datetime
import json
import logging
import os
import tempfile
import time
import zipfile

import requests

from daemons.get_thread import GetJobThread
from scp.models import IncomingDetails

LOG_FORMAT = ('%(levelname)s:%(asctime)s:%(message)s')
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


class InferenceServerDaemon:
    def __init__(self,
                 scp,
                 run_interval: int = 10,
                 timeout: int = 18000):
        self.scp = scp
        self.previous_queue = None
        self.run_interval = run_interval
        self.timeout = timeout
        self.threads = []
        self.cert = "/CERTS/cert.crt"

    def __del__(self):
        for t in self.threads:
            t.join()

    def run(self) -> None:
        while True:
            time.sleep(self.run_interval)
            logging.info("Scanning for newcomers")

            to_remove = []
            for id, details in self.scp.get_queue_dict().items():
                assert isinstance(details, IncomingDetails)
                if (datetime.datetime.now() - details.last_timestamp) > datetime.timedelta(seconds=self.run_interval):
                    logging.info(f"Posting task {str(details)}")
                    res = self.post(incoming_details=details)
                    if res.ok:
                        uid = json.loads(res.content)
                        logging.info(f"Successful post of {details}.")
                        logging.info(f"UID: {uid}")
                        t = GetJobThread(uid=uid,
                                         endpoint=details.endpoint,
                                         timeout=self.timeout)
                        self.threads.append(t)
                        to_remove.append(id)  # Pop from dict
                        t.start()
                    else:
                        logging.info(f"Unsuccessful post to {details.endpoint.scu_ip}: {details.endpoint.scu_port}, {details}")
                        continue

            for id in to_remove:
                self.scp.delete_id_in_queue_dict(id)

    def post(self, incoming_details: IncomingDetails):
        with tempfile.TemporaryFile() as tmp_file:
            with zipfile.ZipFile(tmp_file, "w") as zip_file:
                for fol, subs, files in os.walk(incoming_details.path):
                    for f in files:
                        zip_file.write(os.path.join(fol, f), arcname=f)
            tmp_file.seek(0)

            res = requests.post(incoming_details.endpoint.inference_server_url,
                                params={"model_human_readable_id": incoming_details.endpoint.model_human_readable_id},
                                files={"zip_file": tmp_file},
                                verify=self.cert)
            return res
