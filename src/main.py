import os

import uvicorn as uvicorn

from api.fast_api import DicomNodeAPI
from client.client import Client
from daemon.daemon import Daemon

from database.db import DB
from dicom_networking.scp import SCP

class Environment:
    SCP_IP = "localhost"
    SCP_PORT = 10000
    SCP_AE_TITLE = "DICOM_RECEIVER"
    TEMPORARY_STORAGE = "/tmp/DICOM/"
    LOG_LEVEL = 20
    PYNETDICOM_LOG_LEVEL = "Normal"
    DAEMON_RUN_INTERVAL = 10
    CERT_FILE = "CERT/cert.crt"
    TIMEOUT = 7200
    DB_BASEDIR = "./.data/DB"
    def __init__(self):
        for name in self.__dict__.keys():
            if name in os.environ.keys():
                self.__setattr__(name, os.environ[name])

def main():
    env = Environment()
    scp = SCP(ip=env.SCP_IP,
              port=env.SCP_PORT,
              ae_title=env.SCP_AE_TITLE,
              temporary_storage=env.TEMPORARY_STORAGE,
              log_level=env.LOG_LEVEL,
              pynetdicom_log_level=env.PYNETDICOM_LOG_LEVEL)
    scp.run_scp(blocking=False)

    db = DB(base_dir=env.DB_BASEDIR)
    client = Client(cert=env.CERT_FILE)
    daemon = Daemon(client=client,
                    scp=scp,
                    db=db,
                    run_interval=int(env.DAEMON_RUN_INTERVAL),
                    timeout=int(env.TIMEOUT))
    daemon.start()

    app = DicomNodeAPI(db=db, log_level=env.LOG_LEVEL)
    uvicorn.run(app=app,  # Blocks
                host="localhost",
                port=8181)
    daemon.kill()

if __name__ == "__main__":
    main()
