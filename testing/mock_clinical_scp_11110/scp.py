import logging
import os

import dotenv
from pynetdicom import (
    AE, debug_logger, evt, AllStoragePresentationContexts,
    ALL_TRANSFER_SYNTAXES
)

dotenv.load_dotenv("../../.env")
debug_logger()

LOG_FORMAT = ('%(levelname)s:%(asctime)s:%(message)s')
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logging.info("Outside Main")


class MockClinicalSCP:
    def __init__(self):
        self.dicom_dir = 'CLINICAL_DICOM'
        os.makedirs(self.dicom_dir, exist_ok=True)

    def handle_store(self, event, storage_dir):
        """Handle EVT_C_STORE events."""
        ds = event.dataset

        # Add the File Meta Information
        ds.file_meta = event.file_meta

        tsuid = ds.PatientID
        path = str(os.path.join(storage_dir, tsuid))

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

    def run_scp(self):
        handler = [
            (evt.EVT_C_STORE, self.handle_store, [self.dicom_dir]),
        ]

        try:
            # Create and run
            ae_title = "CLINICAL_AE"
            ip = "127.0.0.1"
            port = 11110
            logging.info(f"Running {ae_title} on {ip}:{str(port)}")

            ae = self.create_accepting_AE(ae_title)
            ae.start_server((ip, port), block=True, evt_handlers=handler)

        except OSError as ose:
            print(
                f'Full error: \r\n{ose} \r\n\r\n Cannot start Association Entity servers. This is likely because the the program is already running, either through VSCode or a terminal. Close the program and try again.')
            raise ose
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    scp = MockClinicalSCP()
    scp.run_scp()