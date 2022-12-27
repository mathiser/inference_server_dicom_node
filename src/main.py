import os

from fingerprint_handler.fingerprint_handler import FingerprintHandler
from dicom_networking.scp import SCP
from database.db import DB
from database.db_daemon import DBDaemon
from models.models import Base

def main():
    db = DB(data_dir=os.environ.get("DATA_DIR"),
            declarative_base=Base)

    scp = SCP(ip=os.environ.get("SCP_IP"),
              port=int(os.environ.get("SCP_PORT")),
              ae_title=os.environ.get("SCP_AE_TITLE"),
              storage_dir=os.environ.get("INCOMING_DIR"),
              log_level=os.environ.get("LOG_LEVEL"),
              pynetdicom_log_level=os.environ.get("PYNETDICOM_LOG_LEVEL"),
              db=db)

    scp.run_scp(blocking=False)

    fp = FingerprintHandler(fingerprint_dir=os.environ.get("FINGERPRINT_DIR"))
    daemon = DBDaemon(db=db,
                      cert_file=os.environ.get("CERT_FILE"),
                      post_timeout_secs=int(os.environ.get("POST_TIMEOUT_SECS")),
                      post_interval=int(os.environ.get("POST_INTERVAL")),
                      post_after=int(os.environ.get("POST_AFTER")),
                      )
    daemon.run()  # Blocks


if __name__ == "__main__":
    main()
