import datetime
import logging
import os
import queue
from typing import Dict

import pydantic
from pynetdicom import AE, evt, StoragePresentationContexts, _config

LOG_FORMAT = ('%(levelname)s:%(asctime)s:%(message)s')


class SeriesInstance(pydantic.BaseModel):
    series_instance_uid: str
    study_description: str
    series_description: str
    sop_class_uid: str
    path: str  # Direct folder to this SeriesInstance


class Assoc(pydantic.BaseModel):
    assoc_id: str
    timestamp: datetime.datetime
    path: str  # Base folder
    series_instances: Dict[str, SeriesInstance]  # Dict[series_instance_uid: SeriesInstance]


class SCP:
    def __init__(self,
                 ae_title: str,
                 ip: str,
                 port: int,
                 storage_dir: str,
                 log_level=10,
                 pynetdicom_log_level="standard",
                 ):

        logging.basicConfig(level=log_level, format=LOG_FORMAT)
        _config.LOG_HANDLER_LEVEL = pynetdicom_log_level

        self.ae_title = ae_title
        self.ip = ip
        self.port = port
        self.storage_dir = storage_dir
        self.ae = None

        self.established_assoc_objs = {}  # container for finished associations
        self.released_assoc_objs = queue.Queue()  # container for finished associations. Should be reached through self.get_incoming()

    def __del__(self):
        if self.ae:
            self.ae.shutdown()

    def get_incoming_queue(self):
        return self.released_assoc_objs

    def update_assoc_obj(self, event, series_instance_uid, study_description, series_description,
                         sop_class_uid):

        # Thread id of incoming
        assoc_id = event.assoc.native_id

        # If top level assoc obj does not exist, create it
        if assoc_id not in self.established_assoc_objs.keys():
            self.established_assoc_objs[assoc_id] = Assoc(assoc_id=assoc_id,
                                                          timestamp=datetime.datetime.now(),
                                                          series_instances={},
                                                          path=os.path.join(self.storage_dir, str(assoc_id)))

        ## If not SeriesInstance exist in self.assoc_obj.series_instances.keys()
        if series_instance_uid not in self.established_assoc_objs[assoc_id].series_instances.keys():
            self.established_assoc_objs[assoc_id].series_instances[series_instance_uid] = SeriesInstance(
                series_instance_uid=series_instance_uid,
                study_description=study_description,
                series_description=series_description,
                sop_class_uid=sop_class_uid,
                path=os.path.join(self.established_assoc_objs[assoc_id].path, sop_class_uid, series_instance_uid)
            )
        return self.established_assoc_objs[assoc_id]

    def handle_store(self, event):
        """Handle EVT_C_STORE events."""
        assoc_id = event.assoc.native_id
        # Get data set from event
        ds = event.dataset

        # Add the File Meta Information
        ds.file_meta = event.file_meta
        series_instance_uid = ds.get("SeriesInstanceUID", "None")
        self.update_assoc_obj(event=event,
                              series_instance_uid=series_instance_uid,
                              study_description=ds.get("StudyDescription", "None"),
                              series_description=ds.get("SeriesDescription", "None"),
                              sop_class_uid=ds.get("SOPClassUID", "None")
                              )

        # Save the dataset using the SOP Instance UID as the filename
        series_instance_folder = os.path.join(self.established_assoc_objs[assoc_id].series_instances[series_instance_uid].path)
        os.makedirs(series_instance_folder, exist_ok=True)
        ds.save_as(os.path.join(series_instance_folder, ds.SOPInstanceUID + ".dcm"), write_like_original=False)

        # Return a 'Success' status
        return 0x0000

    def handle_release(self, event):
        self.released_assoc_objs.put(self.established_assoc_objs[event.assoc.native_id])
        del self.established_assoc_objs[event.assoc.native_id]

    def create_accepting_ae(self):
        self.ae = AE(ae_title=self.ae_title)
        self.ae.supported_contexts = StoragePresentationContexts
        return self.ae

    def run_scp(self, blocking=True):
        handler = [
            (evt.EVT_C_STORE, self.handle_store),
            (evt.EVT_RELEASED, self.handle_release)
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


if __name__ == "__main__":
    scp = SCP(ae_title="test_scp",
              ip="localhost",
              port=10004,
              storage_dir="test_dir",
              pynetdicom_log_level="debug")
    scp.run_scp(blocking=True)
