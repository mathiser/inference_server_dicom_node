import json
import os

import dotenv

from scp.scp import SCP
from database.db import DB
from daemons.inference_server_daemon import InferenceServerDaemon

dotenv.load_dotenv()


def main():
    with open(os.environ.get("SCP_CONFIG_JSON")) as r:
        scp_config = json.loads(r.read())

    scp = SCP(hostname=scp_config["hostname"],
              port=scp_config["port"],
              ae_title=scp_config["ae_title"],
              storage_dir=os.environ.get("INCOMING_DIR"),
              block=False)
    scp.run_scp()

    db = DB(os.environ.get("FINGERPRINT_DIR"))
    daemon = InferenceServerDaemon(scp=scp,
                                   db=db,
                                   cert_file=os.environ.get("CERT_FILE"),
                                   timeout=7200,
                                   run_interval=10)
    daemon.run()  # Blocks


if __name__ == "__main__":
    main()
