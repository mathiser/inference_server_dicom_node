import os

import dotenv

from scp.scp import SCP
from database.db import DB
from daemons.inference_server_daemon import InferenceServerDaemon

dotenv.load_dotenv()

def main():
    db = DB("./dicom_endpoints")

    scp = SCP(dcm_node_endpoints=db.get_endpoints(), db=db)
    scp.run_all_scps()

    daemon = InferenceServerDaemon(scp=scp, run_interval=15)
    daemon.run()

if __name__=="__main__":
    main()