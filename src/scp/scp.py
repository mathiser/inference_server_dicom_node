import logging
import os
import shutil
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from pynetdicom import (
    AE, debug_logger, evt, AllStoragePresentationContexts,
    ALL_TRANSFER_SYNTAXES
)
from models import Incoming

#debug_logger()

LOG_FORMAT = ('%(levelname)s:%(asctime)s:%(message)s')
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logging.info("Outside Main")


class SCP:
    def __init__(self,
                 ae_title: str,
                 hostname: str,
                 port: int,
                 storage_dir: str,
                 block: bool = False):

        self.ae_title = ae_title
        self.hostname = hostname
        self.port = port
        self.block = block
        self.storage_dir = storage_dir

        self.queue_dict = {}

    def get_queue_dict(self):
        return self.queue_dict

    def delete_id_in_queue_dict(self, id):
        try:
            logging.info(f"[ ] Deleting {id}")
            shutil.rmtree(self.queue_dict[id].path)
            del self.queue_dict[id]
            logging.info(f"[X] Deleting {id}")
        except Exception as e:
            logging.error(e)

    def handle_store(self, event):
        """Handle EVT_C_STORE events."""
        ds = event.dataset

        # Add the File Meta Information
        ds.file_meta = event.file_meta
        pid = ds.PatientID
        modality = ds.Modality.upper()

        try:
            study_description = ds.StudyDescription.upper()
        except:
            study_description = "None"

        logging.info(f"Received dicom: Study description: {study_description}, Modality: {modality}")

        path = os.path.join(self.storage_dir, pid, modality, study_description)
        # make dir for the incoming
        os.makedirs(path, exist_ok=True)

        if path not in self.queue_dict.keys():
            self.queue_dict[path] = Incoming(path=path,
                                             last_timestamp=event.timestamp,
                                             first_timestamp=event.timestamp,
                                             PatientID=pid,
                                             Modality=modality,
                                             StudyDescription=study_description)
        else:
            self.queue_dict[path].last_timestamp = event.timestamp

        # Save the dataset using the SOP Instance UID as the filename
        ds.save_as(os.path.join(path, ds.SOPInstanceUID + ".dcm"), write_like_original=False)

        # Return a 'Success' status
        return 0x0000

    def create_accepting_ae(self):
        ae_temp = AE(ae_title=self.ae_title)
        storage_sop_classes = [
            cx.abstract_syntax for cx in AllStoragePresentationContexts
        ]
        for uid in storage_sop_classes:
            ae_temp.add_supported_context(uid, ALL_TRANSFER_SYNTAXES)

        ae_temp.add_supported_context('1.2.840.10008.1.1', ALL_TRANSFER_SYNTAXES)  # Verification SOP Class
        ae_temp.add_supported_context('1.2.840.10008.3.1.1.1', ALL_TRANSFER_SYNTAXES)  # DICOM Application Context Name
        ae_temp.add_supported_context('1.2.840.10008.5.1.4.1.1.11.1', ALL_TRANSFER_SYNTAXES)  # Not sure
        return ae_temp

    def run_scp(self):
        handler = [
            (evt.EVT_C_STORE, self.handle_store),
        ]

        try:
            logging.info(
                f"Starting SCP -- InferenceServerDicomNode: {self.hostname}:{str(self.port)}")

            # Create and run
            ae = self.create_accepting_ae()
            ae.start_server((self.hostname, self.port), block=self.block, evt_handlers=handler)

        except OSError as ose:
            logging.error(
                f'Full error: \r\n{ose} \r\n\r\n Cannot start Association Entity servers. This is likely because the the program is already running, either through VSCode or a terminal. Close the program and try again.')
            raise ose


if __name__ == "__main__":
    scp = SCP(hostname="localhost", port=12999, ae_title="TestSCP", storage_dir="INCOMING", block=True)
    scp.run_scp()
