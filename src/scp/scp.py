import logging
import os
import shutil
import sys
import traceback

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from pynetdicom import AE, evt, StoragePresentationContexts, _config
from models import Incoming

LOG_FORMAT = ('%(levelname)s:%(asctime)s:%(message)s')
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
_config.LOG_HANDLER_LEVEL = os.environ.get("PYNETDICOM_LOG_LEVEL")


class SCP:
    def __init__(self,
                 ae_title: str,
                 hostname: str,
                 port: int,
                 storage_dir: str,
                 delete_on_post: bool,
                 block: bool = False):

        self.ae_title = ae_title
        self.hostname = hostname
        self.port = port
        self.block = block
        self.storage_dir = storage_dir
        self.delete_on_post = delete_on_post
        self.queue_dict = {}

    def get_queue_dict(self):
        return self.queue_dict

    def delete_id_in_queue_dict(self, id):
        try:
            if self.delete_on_post:
                logging.info(f"Deleting {id} from disk")
                shutil.rmtree(self.queue_dict[id].path)

            logging.info(f"Deleting {id} from incoming dict")
            del self.queue_dict[id]

        except Exception as e:
            traceback.print_exc()
            logging.error(e)

    def handle_store(self, event):
        """Handle EVT_C_STORE events."""
        ds = event.dataset

        # Add the File Meta Information
        ds.file_meta = event.file_meta
        pid = ds.PatientID
        modality = ds.Modality
        try:
            sop_uid = ds.SOPClassUID
        except:
            sop_uid = "None"

        try:
            study_description = ds.StudyDescription
        except:
            study_description = "None"

        try:
            series_description = ds.SeriesDescription
        except:
            series_description = "None"

        logging.info(f"Received: Study description: {study_description}, Series description: {series_description},"
                     f" Modality: {modality}, SOPClassUID: {sop_uid}")

        path = os.path.join(self.storage_dir, pid, study_description, series_description, modality, sop_uid)
        # make dir for the incoming
        os.makedirs(path, exist_ok=True)

        if path not in self.queue_dict.keys():
            self.queue_dict[path] = Incoming(path=path,
                                             last_timestamp=event.timestamp,
                                             first_timestamp=event.timestamp,
                                             PatientID=pid,
                                             Modality=modality,
                                             StudyDescription=study_description,
                                             SeriesDescription=series_description,
                                             SOPClassUID=sop_uid)
        else:
            self.queue_dict[path].last_timestamp = event.timestamp

        # Save the dataset using the SOP Instance UID as the filename
        ds.save_as(os.path.join(path, ds.SOPInstanceUID + ".dcm"), write_like_original=False)

        # Return a 'Success' status
        return 0x0000

    def create_accepting_ae(self):
        ae = AE(ae_title=self.ae_title)
        ae.supported_contexts = StoragePresentationContexts
        return ae

    def run_scp(self):
        handler = [
            (evt.EVT_C_STORE, self.handle_store),
        ]

        try:
            logging.info(
                f"Starting SCP -- InferenceServerDicomNode: {self.hostname}:{str(self.port)} - {self.ae_title}")

            # Create and run
            ae = self.create_accepting_ae()
            ae.start_server((self.hostname, self.port), block=self.block, evt_handlers=handler)

        except OSError as ose:
            logging.error(
                f'Full error: \r\n{ose} \r\n\r\n Cannot start Association Entity servers')
            raise ose


if __name__ == "__main__":
    scp = SCP(hostname="localhost", port=12999, ae_title="TestSCP", storage_dir="INCOMING", delete_on_post=True, block=True)
    scp.run_scp()
