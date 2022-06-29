import logging
import os
import tempfile
import threading
import time
import zipfile
from urllib.parse import urljoin

import requests
from pydicom import dcmread
from pynetdicom import AE, debug_logger, StoragePresentationContexts

from models import Fingerprint, SCU

LOG_FORMAT = ('%(levelname)s:%(asctime)s:%(message)s')
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logging.info("Outside Main")


class GetJobThread(threading.Thread):
    def __init__(self,
                 uid: str,
                 fingerprint: Fingerprint,
                 cert_file: str,
                 run_interval: int = 15,
                 timeout: int = 3600,
                 *args,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.uid = uid
        self.fingerprint = fingerprint
        self.run_interval = run_interval
        self.timeout = timeout
        self.cert = cert_file

    def run(self) -> None:
        counter = 0
        while counter < self.timeout:
            try:
                res = requests.get(url=urljoin(self.fingerprint.inference_server_url, self.uid),
                                   verify=self.cert)
                logging.info(res)
                logging.info(str(res.content))
                if res.ok:
                    logging.info("POSTING RETURNED SHIT TO CLINICAL NODE (not)")
                    with tempfile.TemporaryFile() as tmp_file:
                        tmp_file.write(res.content)
                        tmp_file.seek(0)

                        with tempfile.TemporaryDirectory() as tmp_dir, zipfile.ZipFile(tmp_file, "r") as zip_file:
                            zip_file.extractall(tmp_dir)
                            for scu in self.fingerprint.scus:
                                self.post_to_dicom_node(dicom_dir=tmp_dir, scu=scu)
                    return
                if res.status_code == 552:
                    logging.error(str(res))
                    logging.error("Quitting this task - contact admin for help")
                    return

            except Exception as e:
                logging.error(e)

            logging.info(f"WAITING FOR RETURNED SHIT TO CLINICAL NODE {str(counter)} on UID {self.uid}")
            time.sleep(self.run_interval)
            counter += self.run_interval


    def post_to_dicom_node(self, scu: SCU, dicom_dir):
        debug_logger()

        ae = AE()
        ae.requested_contexts = StoragePresentationContexts

        assoc = ae.associate(scu.scu_ip, scu.scu_port)
        if assoc.is_established:
            # Use the C-STORE service to send the dataset
            # returns the response status as a pydicom Dataset
            for file in os.listdir(dicom_dir):
                p = os.path.join(dicom_dir, file)
                ds = dcmread(p)
                status = assoc.send_c_store(ds)

                # Check the status of the storage request
                if status:
                    # If the storage request succeeded this will be 0x0000
                    logging.info('C-STORE request status: 0x{0:04x}'.format(status.Status))
                else:
                    logging.info('Connection timed out, was aborted or received invalid response')

            # Release the association
            assoc.release()
        else:
            logging.error('Association rejected, aborted or never connected')