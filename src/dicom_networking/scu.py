from pydicom import dcmread
from pynetdicom import AE, StoragePresentationContexts

from models.models import Destination

import logging
import os

def post_folder_to_dicom_node(destination: Destination, dicom_dir) -> bool:
    ae = AE()
    ae.requested_contexts = StoragePresentationContexts

    assoc = ae.associate(destination.scu_ip, destination.scu_port, ae_title=destination.scu_ae_title)
    if assoc.is_established:
        # Use the C-STORE service to send the dataset
        # returns the response status as a pydicom Dataset
        logging.info(f'Posting {dicom_dir} to {str(destination.__dict__)}')
        for fol, subs, files in os.walk(dicom_dir):
            for file in files:
                p = os.path.join(fol, file)
                ds = dcmread(p)
                status = assoc.send_c_store(ds)

                # Check the status of the storage request
                if status:
                    pass
                    # If the storage request succeeded this will be 0x0000
                    # logging.info('C-STORE request status: 0x{0:04x}'.format(status.Status))
                else:
                    logging.info('Connection timed out, was aborted or received invalid response')

        # Release the association
        assoc.release()
        return True
    else:
        logging.error('Association rejected, aborted or never connected')
        return False