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
              delete_on_post=bool(os.environ.get("DELETE_ON_POST")),
              block=False)
    scp.run_scp()

    db = DB(os.environ.get("FINGERPRINT_DIR"))
    daemon = InferenceServerDaemon(scp=scp,
                                   db=db,
                                   cert_file=os.environ.get("CERT_FILE"),
                                   post_timeout=int(os.environ.get("POST_TIMEOUT")),
                                   post_interval=int(os.environ.get("POST_INTERVAL")),
                                   post_after=int(os.environ.get("POST_AFTER")),
                                   )
    daemon.run()  # Blocks


if __name__ == "__main__":
    main()
