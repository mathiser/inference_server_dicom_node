import logging
import os
import shutil
from typing import List

from pynetdicom import (
    AE, debug_logger, evt, AllStoragePresentationContexts,
    ALL_TRANSFER_SYNTAXES
)

#
from database.db import DB
from database.models import DCMNodeEndpoint
from scp.models import IncomingDetails

debug_logger()

LOG_FORMAT = ('%(levelname)s:%(asctime)s:%(message)s')
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logging.info("Outside Main")


class SCP:
    def __init__(self, dcm_node_endpoints: List[DCMNodeEndpoint], db: DB):
        self.dcm_node_endpoints = dcm_node_endpoints  # {"ip": str, "port": int, "model_human_readable_id": str}

        self.db = db

        self.aes = []
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

    def handle_store(self, event, endpoint: DCMNodeEndpoint):
        """Handle EVT_C_STORE events."""
        ds = event.dataset

        # Add the File Meta Information
        ds.file_meta = event.file_meta

        tsuid = ds.file_meta.TransferSyntaxUID
        path = str(os.path.join(endpoint.scp_storage_dir, tsuid))

        if tsuid not in self.queue_dict.keys():
            self.queue_dict[ds.file_meta.TransferSyntaxUID] = IncomingDetails(endpoint=endpoint,
                                                                              path=path,
                                                                              last_timestamp=event.timestamp,
                                                                              first_timestamp=event.timestamp,
                                                                              TransferSyntaxUID=tsuid)
        else:
            self.queue_dict[tsuid].last_timestamp = event.timestamp

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

    def run_scp(self, endpoint: DCMNodeEndpoint, block: bool = False):
        handler = [
            (evt.EVT_C_STORE, self.handle_store, [endpoint]),
        ]

        try:
            logging.info(f"Starting SCP -- InferenceServer model: {endpoint.model_human_readable_id} on: {endpoint.scp_ip}:{str(endpoint.scp_port)}")

            # Create and run
            ae = self.create_accepting_AE(endpoint.scp_ae_title)
            self.aes.append(ae)
            ae.start_server((endpoint.scp_ip, endpoint.scp_port), block=block, evt_handlers=handler)

        except OSError as ose:
            logging.error(
                f'Full error: \r\n{ose} \r\n\r\n Cannot start Association Entity servers. This is likely because the the program is already running, either through VSCode or a terminal. Close the program and try again.')
            raise ose

    def run_all_scps(self):
        for endpoint in self.dcm_node_endpoints:
            self.run_scp(endpoint=endpoint, block=False)
