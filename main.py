import os

import dotenv

from scp.scp import SCP
from database.db import DB
from daemons.inference_server_daemon import InferenceServerDaemon

dotenv.load_dotenv()

def main():
    db = DB(os.environ.get("SCP_DETAILS_JSON_PATH"))

    scp = SCP(scp_endpoints=db.get_scp_details(), db=db, dicom_dir="DICOM")
    scp.run_all_scps()

    daemon = InferenceServerDaemon(scp=scp, inference_server_endpoint=os.environ.get("INFERENCE_SERVER_TASK_ENDPOINT"), run_interval=15)
    daemon.run()
    #post_thread.start()

if __name__=="__main__":
    main()