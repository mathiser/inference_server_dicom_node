import datetime
import json
import logging
import os
import tempfile
import time
import zipfile

import requests

from daemons.get_thread import GetJobThread
from models import Incoming

from database.db import DB

from models import Fingerprint
from scp.scp import SCP

LOG_FORMAT = ('%(levelname)s:%(asctime)s:%(message)s')
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


class InferenceServerDaemon:
    def __init__(self,
                 scp: SCP,
                 db: DB,
                 cert_file: str,
                 post_interval: int,
                 post_after: int,
                 post_timeout: int,
                 ):
        self.scp = scp
        self.post_interval = post_interval
        self.post_after = post_after
        self.post_timeout = post_timeout
        self.threads = []
        self.db = db
        self.cert = cert_file

    def __del__(self):
        for t in self.threads:
            t.join()

    def run(self) -> None:
        while True:
            time.sleep(self.post_interval)
            to_remove = set()
            for id, incoming in self.scp.get_queue_dict().items():
                assert isinstance(incoming, Incoming)

                if self.is_ready_to_post(incoming):
                    logging.info(f"{str(incoming.path)} has been untouched for {str(self.post_after)} seconds.")

                    fingerprints = self.db.get_fingerprint_from_incoming(incoming)
                    logging.info(f"Found {str(len(fingerprints))} matching fingerprints for {str(incoming.path)}")

                    if len(fingerprints) == 0:
                        logging.info(f"Removing: {str(incoming.path)}")
                        to_remove.add(id)  # Pop from dict
                        continue

                    # Post for each model
                    for fingerprint in fingerprints:
                        logging.info(f"Shipping off {str(incoming.path)} to {fingerprint.inference_server_url} "
                                     f"on model: {fingerprint.model_human_readable_id}")
                        res = self.post(incoming=incoming,
                                        fingerprint=fingerprint)
                        logging.info(f"{str(res)}: {str(res.content)} - {fingerprint.model_human_readable_id}")
                        if res.ok:
                            uid = json.loads(res.content)
                            logging.info(f"Successful post of {incoming.path} with UID: {uid}")
                            t = GetJobThread(uid=uid,
                                             fingerprint=fingerprint,
                                             cert_file=self.cert,
                                             get_timeout=int(os.environ.get("GET_TIMEOUT")),
                                             get_interval=int(os.environ.get("GET_INTERVAL")))
                            self.threads.append(t)
                            t.start()

                            to_remove.add(id)
                        else:
                            logging.error(f"{str(res)}: Unsuccessful post to {incoming.fingerprint.scu_ip}: "
                                          f"{incoming.fingerprint.scu_port}, {incoming}")

            for id in to_remove:
                self.scp.delete_id_in_queue_dict(id)

    def post(self, incoming: Incoming, fingerprint: Fingerprint):
        with tempfile.TemporaryFile() as tmp_file:
            with zipfile.ZipFile(tmp_file, "w") as zip_file:
                for fol, subs, files in os.walk(incoming.path):
                    for f in files:
                        zip_file.write(os.path.join(fol, f), arcname=f)
            tmp_file.seek(0)

            res = requests.post(url=fingerprint.inference_server_url,
                                params={"model_human_readable_id": fingerprint.model_human_readable_id},
                                files={"zip_file": tmp_file},
                                verify=self.cert)
            return res

    def is_ready_to_post(self, incoming: Incoming):
        return (datetime.datetime.now() - incoming.last_timestamp) > datetime.timedelta(seconds=self.post_after)
