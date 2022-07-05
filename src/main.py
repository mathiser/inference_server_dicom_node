import json
import os

import dotenv

from scp.scp import SCP
from database.db import DB
from daemons.inference_server_daemon import InferenceServerDaemon

dotenv.load_dotenv()


def main():
    scp = SCP(hostname=os.environ.get("SCP_HOSTNAME"),
              port=int(os.environ.get("SCP_PORT")),
              ae_title=os.environ.get("SCP_AE_TITLE"),
              storage_dir=os.environ.get("INCOMING_DIR"),
              block=False)
    scp.run_scp()

    db = DB(os.environ.get("FINGERPRINT_DIR"))
    daemon = InferenceServerDaemon(scp=scp,
                                   db=db,
                                   cert_file=os.environ.get("CERT_FILE"),
                                   timeout=int(os.environ.get("GET_TIMEOUT")),
                                   run_interval=int(os.environ.get("RUN_INTERVAL")),
                                   send_after=int(os.environ.get("SEND_AFTER")),
                                   delete_on_send=bool(os.environ.get("DELETE_ON_SEND"))
                                   )
    daemon.run()  # Blocks


if __name__ == "__main__":
    main()
