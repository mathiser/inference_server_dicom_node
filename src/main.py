import logging
import os
from typing import Union

import uvicorn as uvicorn

from api.fast_api import DicomNodeAPI
from client.client import Client
from daemon.daemon import Daemon

from database.db import DB
from dicom_networking.scp import SCP


class Main:
    def __init__(self,
                 SCP_IP: str = "localhost",
                 SCP_PORT: int = 10000,
                 SCP_AE_TITLE: str = "DICOM_RECEIVER",
                 TEMPORARY_STORAGE: str = "/tmp/DICOM/",
                 LOG_LEVEL: int = 20,
                 PYNETDICOM_LOG_LEVEL: str = "Normal",
                 DAEMON_RUN_INTERVAL: int = 10,
                 CERT_FILE: Union[str, bool] = "CERT/cert.crt",
                 TIMEOUT: int = 7200,
                 DB_BASEDIR: str = "./.data/DB",
                 API_PORT: int = 8124):
        self.SCP_IP = SCP_IP
        self.SCP_PORT = SCP_PORT
        self.SCP_AE_TITLE = SCP_AE_TITLE
        self.TEMPORARY_STORAGE= TEMPORARY_STORAGE
        self.LOG_LEVEL = LOG_LEVEL
        self.PYNETDICOM_LOG_LEVEL=PYNETDICOM_LOG_LEVEL
        self.DAEMON_RUN_INTERVAL=DAEMON_RUN_INTERVAL
        self.CERT_FILE = CERT_FILE
        self.TIMEOUT=TIMEOUT
        self.DB_BASEDIR = DB_BASEDIR
        self.API_PORT = API_PORT

        for name in self.__dict__.keys():
            if name in os.environ.keys():
                self.__setattr__(name, os.environ[name])
        LOG_FORMAT = '%(levelname)s:%(asctime)s:%(message)s'

        logging.basicConfig(level=int(self.LOG_LEVEL), format=LOG_FORMAT)
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Instantiated Dicom Node with params: {self.__dict__}")

    def run(self):
        scp = SCP(ip=self.SCP_IP,
                  port=self.SCP_PORT,
                  ae_title=self.SCP_AE_TITLE,
                  temporary_storage=self.TEMPORARY_STORAGE,
                  log_level=self.LOG_LEVEL,
                  pynetdicom_log_level=self.PYNETDICOM_LOG_LEVEL)

        scp.run_scp(blocking=False)

        db = DB(base_dir=self.DB_BASEDIR)
        client = Client(cert=self.CERT_FILE)
        daemon = Daemon(client=client,
                        scp=scp,
                        db=db,
                        run_interval=int(self.DAEMON_RUN_INTERVAL),
                        timeout=int(self.TIMEOUT))
        daemon.start()

        app = DicomNodeAPI(db=db, log_level=self.LOG_LEVEL)
        uvicorn.run(app=app,  # Blocks
                    host="localhost",
                    port=int(self.API_PORT))
        daemon.kill()


if __name__ == "__main__":
    m = Main()
    m.run()
