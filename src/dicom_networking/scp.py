import logging
import os

from pynetdicom import AE, evt, StoragePresentationContexts, _config

from database.db import DB

LOG_FORMAT = ('%(levelname)s:%(asctime)s:%(message)s')


class SCP:
    def __init__(self,
                 ae_title: str,
                 ip: str,
                 port: int,
                 storage_dir: str,
                 db: DB,
                 log_level=10,
                 pynetdicom_log_level="",
                 ):
        self.db = db
        self.ae_title = ae_title
        self.ip = ip
        self.port = port
        self.storage_dir = storage_dir

        logging.basicConfig(level=log_level, format=LOG_FORMAT)
        _config.LOG_HANDLER_LEVEL = pynetdicom_log_level

    def __del__(self):
        self.shutdown_ae()
    def handle_store(self, event):
        """Handle EVT_C_STORE events."""
        ds = event.dataset

        # Add the File Meta Information
        ds.file_meta = event.file_meta
        pid = ds.get("PatientID", "None")
        series_instance_uid = ds.get("SeriesInstanceUID", "None")
        modality = ds.get("Modality", "None")
        sop_uid = ds.get("SOPClassUID", "None")
        study_description = ds.get("StudyDescription", "None")
        series_description = ds.get("SeriesDescription", "None")

        logging.info(f"Received: SeriesInstanceUID: {series_instance_uid} Study description: {study_description}, Series description: {series_description},"
                     f" Modality: {modality}, SOPClassUID: {sop_uid}")

        inc = self.db.upsert_incoming(timestamp=event.timestamp,
                                      patient_id=pid,
                                      series_instance_uid=series_instance_uid,
                                      modality=modality,
                                      study_description=study_description,
                                      series_description=series_description,
                                      sop_class_uid=sop_uid,
                                      )

        # Save the dataset using the SOP Instance UID as the filename
        ds.save_as(os.path.join(inc.path, ds.SOPInstanceUID + ".dcm"), write_like_original=False)

        # Return a 'Success' status
        return 0x0000
    def create_accepting_ae(self):
        ae = AE(ae_title=self.ae_title)
        ae.supported_contexts = StoragePresentationContexts
        return ae

    def shutdown_ae(self):
        assert self.ae
        self.ae.shutdown()

    def run_scp(self, blocking=True):
        handler = [
            (evt.EVT_C_STORE, self.handle_store)
        ]

        try:
            logging.info(
                f"Starting SCP -- InferenceServerDicomNode: {self.ip}:{str(self.port)} - {self.ae_title}")

            # Create and run
            self.ae = self.create_accepting_ae()
            self.ae.start_server((self.ip, self.port), block=blocking, evt_handlers=handler)

        except OSError as ose:
            logging.error(
                f'Full error: \r\n{ose} \r\n\r\n Cannot start Association Entity servers')
            raise ose
