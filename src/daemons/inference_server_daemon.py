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
                 run_interval: int,
                 send_after: int,
                 timeout: int,
                 delete_on_send: bool
                 ):
        self.scp = scp
        self.run_interval = run_interval
        self.send_after = send_after
        self.timeout = timeout
        self.threads = []
        self.db = db
        self.delete_on_send = delete_on_send
        self.cert = cert_file

    def __del__(self):
        for t in self.threads:
            t.join()

    def run(self) -> None:
        while True:
            time.sleep(self.run_interval)
            to_remove = set()
            for id, incoming in self.scp.get_queue_dict().items():
                assert isinstance(incoming, Incoming)

                if self.is_ready_to_post(incoming):
                    logging.info(f"{str(incoming)} is untouched for {str(self.send_after)} seconds.")

                    fingerprints = self.db.get_fingerprint_from_incoming(incoming)
                    logging.info(f"Found {str(len(fingerprints))} matching fingerprints for {str(incoming)}")

                    if len(fingerprints) == 0:
                        logging.info(f"Removing: {str(incoming)}")
                        to_remove.add(id)  # Pop from dict
                        continue

                    # Post for each model
                    for fingerprint in fingerprints:
                        logging.info(f"... on matching models for {str(incoming.path)}: {str([n for n in fingerprint])}")
                        res = self.post(incoming=incoming,
                                        fingerprint=fingerprint)
                        logging.info(res)
                        logging.info(str(res.content))
                        if res.ok:
                            uid = json.loads(res.content)
                            logging.info(f"Successful post of {incoming}.")
                            logging.info(f"UID: {uid}")
                            t = GetJobThread(uid=uid,
                                             fingerprint=fingerprint,
                                             timeout=self.timeout,
                                             cert_file=self.cert)
                            self.threads.append(t)
                            t.start()

                            if self.delete_on_send:
                                to_remove.add(id)
                        else:
                            print(res)
                            logging.error(f"Unsuccessful post to {incoming.fingerprint.scu_ip}: {incoming.fingerprint.scu_port}, {incoming}")

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
        return (datetime.datetime.now() - incoming.last_timestamp) > datetime.timedelta(seconds=self.send_after)
