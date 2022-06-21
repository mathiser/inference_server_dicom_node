import logging
import os
from typing import List, Dict

from pynetdicom import (
    AE, debug_logger, evt, AllStoragePresentationContexts,
    ALL_TRANSFER_SYNTAXES
)

#
from database.db import DB

debug_logger()

LOG_FORMAT = ('%(levelname)s:%(asctime)s:%(message)s')
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logging.info("Outside Main")


class SCP:
    def __init__(self, scp_endpoints: List[Dict], db: DB, dicom_dir: str = "DICOM"):
        self.scp_endpoints = scp_endpoints  # {"ip": str, "port": int, "model_human_readable_id": str}
        self.dicom_dir = dicom_dir
        self.alive = True
        os.makedirs(self.dicom_dir, exist_ok=True)
        self.db = db

        self.aes = []
        self.queue_dict = {}

    def get_alive(self):
        return self.alive

    def handle_store(self, event, storage_dir, model_human_readable_id):
        """Handle EVT_C_STORE events."""
        ds = event.dataset

        # Add the File Meta Information
        ds.file_meta = event.file_meta

        tsuid = ds.file_meta.TransferSyntaxUID
        path = str(os.path.join(storage_dir, tsuid))

        if tsuid not in self.queue_dict.keys():
            self.queue_dict[ds.file_meta.TransferSyntaxUID] = {"model_human_readable_id": model_human_readable_id,
                                                               "path": path,
                                                               "last_timestamp": event.timestamp,
                                                               "first_timestamp": event.timestamp,
                                                               "TransferSyntaxUID": tsuid}
        else:
            self.queue_dict[tsuid]["last_timestamp"] = event.timestamp

        # make dir for the incoming
        os.makedirs(path, exist_ok=True)

        # Save the dataset using the SOP Instance UID as the filename
        ds.save_as(os.path.join(path, ds.SOPInstanceUID + ".dcm"), write_like_original=False)

        # Return a 'Success' status
        return 0x0000

    def create_accepting_AE(self, title):
        ae_temp = AE(ae_title=title)
        storage_sop_classes = [
            cx.abstract_syntax for cx in AllStoragePresentationContexts
        ]
        for uid in storage_sop_classes:
            ae_temp.add_supported_context(uid, ALL_TRANSFER_SYNTAXES)

        ae_temp.add_supported_context('1.2.840.10008.1.1', ALL_TRANSFER_SYNTAXES)  # Verification SOP Class
        ae_temp.add_supported_context('1.2.840.10008.3.1.1.1', ALL_TRANSFER_SYNTAXES)  # DICOM Application Context Name
        ae_temp.add_supported_context('1.2.840.10008.5.1.4.1.1.11.1', ALL_TRANSFER_SYNTAXES)  # Not sure
        return ae_temp

    def run_scp(self, ip: str, port: str, ae_title: str, model_human_readable_id: str, block: bool):
        handler = [
            (evt.EVT_C_STORE, self.handle_store, [self.dicom_dir, model_human_readable_id]),
        ]

        try:
            logging.info(f"Starting SCP -- InferenceServer model: {model_human_readable_id} on: {ip}:{str(port)}")

            # Create and run
            ae = self.create_accepting_AE(ae_title)
            self.aes.append(ae)
            ae.start_server((ip, int(port)), block=block, evt_handlers=handler)

        except OSError as ose:
            print(
                f'Full error: \r\n{ose} \r\n\r\n Cannot start Association Entity servers. This is likely because the the program is already running, either through VSCode or a terminal. Close the program and try again.')
            raise ose

    def run_all_scps(self):
        for i, scp_details in enumerate(self.scp_endpoints):
            self.run_scp(**scp_details, block=False) # Being blocked by Inference_daemon. #block=(i + 1 == len(self.scp_endpoints)))  # Block if last element
