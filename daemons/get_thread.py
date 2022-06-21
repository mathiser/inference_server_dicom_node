import glob
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

LOG_FORMAT = ('%(levelname)s:%(asctime)s:%(message)s')
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logging.info("Outside Main")


class GetJobThread(threading.Thread):
    def __init__(self, uid: str, inference_server_endpoint, run_interval: int = 15, timeout: int = 3600, *args,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.uid = uid
        self.inference_server_endpoint = inference_server_endpoint
        self.run_interval = run_interval
        self.timeout = timeout

    def run(self) -> None:
        counter = 0
        while counter < self.timeout:
            res = self.get()
            if res.ok:
                logging.info("POSTING RETURNED SHIT TO CLINICAL NODE (not)")
                with tempfile.TemporaryFile() as tmp_file:
                    tmp_file.write(res.content)
                    tmp_file.seek(0)

                    with tempfile.TemporaryDirectory() as tmp_dir, zipfile.ZipFile(tmp_file, "r") as zip_file:
                        zip_file.extractall(tmp_dir)
                        print(os.listdir(tmp_dir))
                        #os.system(f"storescu 127.0.0.1 11110 {tmp_dir}/*")
                        self.post_to_dicom_node(tmp_dir)

                return

            else:
                logging.info(f"WAITING FOR RETURNED SHIT TO CLINICAL NODE {str(counter)} on UID {self.uid}")
                time.sleep(self.run_interval)
                counter += self.run_interval

    def get(self):
        return requests.get(url=urljoin(self.inference_server_endpoint, self.uid),
                            verify="certs/cert.crt")

    def post_to_dicom_node(self, dicom_dir):
        debug_logger()

        ae = AE()
        ae.requested_contexts = StoragePresentationContexts

        assoc = ae.associate("127.0.0.1", 11110)
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
                    print('C-STORE request status: 0x{0:04x}'.format(status.Status))
                else:
                    print('Connection timed out, was aborted or received invalid response')

            # Release the association
            assoc.release()
        else:
            print('Association rejected, aborted or never connected')