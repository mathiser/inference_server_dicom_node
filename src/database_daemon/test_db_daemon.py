import time
import unittest

from client.mock_client import MockClient
from database_daemon.db_daemon import DBDaemon
from database.tests.test_db import TestDB
from dicom_networking.tests.test_scp import TestSCP
from fingerprint_database.tests.test_fingerprint_handler import TestFingerprintHandler


class TestDBDaemon(unittest.TestCase):
    def setUp(self) -> None:
        self.db_tests = TestDB()
        self.db_tests.setUp()
        self.db = self.db_tests.db
        self.fp_handler_tests = TestFingerprintHandler()
        self.fp_handler_tests.setUp()
        self.fp_handler = self.fp_handler_tests.fp_handler
        self.db_daemon = DBDaemon(db=self.db,
                                  task_expire_after_secs=10,
                                  daemon_run_interval_secs=3,
                                  incoming_expire_after_secs=3,
                                  incoming_idle_after_secs=5,
                                  client=MockClient(cert=False),
                                  fp=self.fp_handler
                                  )

    def tearDown(self) -> None:
        self.db_tests.tearDown()

    def test_set_idle_flag_on_incomings(self):
        inc = self.db_tests.test_burst_insert_incoming()

        self.assertFalse(inc.is_idle)

        self.db_daemon.run_set_idle_flag_on_incomings()
        echo_inc = self.db.get_incoming(inc.id)
        self.assertFalse(echo_inc.is_idle)

        time.sleep(self.db_daemon.incoming_idle_after_secs)
        self.db_daemon.run_set_idle_flag_on_incomings()
        echo_inc = self.db.get_incoming(inc.id)
        self.assertTrue(echo_inc.is_idle)

    def test_run_fingerprinting_to_add_tasks(self):
        inc = self.db_tests.test_burst_insert_incoming()
        fp = {"sub_fingerprints": [
            {
                "modality_exp": inc.Modality,
                "sop_class_uid_exp": inc.SOPClassUID[1:4],
                "exclude_exp": "",
                "study_description_exp": "",
                "series_description_exp": "",
                "zip_path": inc.Modality,
            }
        ],
            "zip_path": "/MRI",
            "inference_server_url": "http://localhost:8000/api/tasks/",
            "model_human_readable_id": "cns_t1_oars",
            "scus": [{"scu_ip": "localhost",
                      "scu_port": 11110,
                      "scu_ae_title": "DICOM_ENDPOINT_AE"}
                     ]}

        self.db.update_incoming(incoming_id=inc.id,
                                is_idle=True)  ## Or else tasks script won't recognize the incoming.
        self.fp_handler_tests.dump_fingerprint_to_folder(self.fp_handler.fingerprint_dir, fp=fp)
        self.fp_handler.load_fingerprints()
        self.db_daemon.run_fingerprint_post_delete_tasks()
        tasks = self.db.get_tasks()
        print(tasks)

    #   self.assertIsNotNone(tasks)
    #   self.assertEqual(len(tasks), 1)
    #   [self.assertEqual(t.status, 1) for t in tasks]

    # def test_run_fingerprinting_to_add_tasks_repeated_runs(self):
    #     inc = self.db_tests.test_burst_insert_incoming()
    #     fp = {"sub_fingerprints":
    #         [
    #             {
    #                 "modality_exp": "MR",
    #                 "sop_class_uid_exp": "1.12.123.1234.12345",
    #                 "exclude_exp": "a^",
    #                 "study_description_exp": "",
    #                 "series_description_exp": "Test",
    #                 "zip_path": "MR",
    #
    #             }
    #         ],
    #         "inference_server_url": "http://localhost:8000/api/tasks/",
    #         "model_human_readable_id": "cns_t1_oars",
    #         "scus": [{"scu_ip": "localhost",
    #                   "scu_port": 11110,
    #                   "scu_ae_title": "DCM_ENDPOINT_AE"}
    #                  ]}
    #     self.db.update_incoming(incoming_id=inc.id,
    #                             is_idle=True)  ## Or else tasks script won't recognize the incoming.
    #     self.fp_handler_tests.dump_fingerprint_to_folder(self.fp_handler.fingerprint_dir, fp=fp)
    #     self.fp_handler.load_fingerprints()
    #     self.db_daemon.run_fingerprint_post_delete_tasks()
    #     self.db_daemon.run_fingerprinting_add_tasks()
    #     self.db_daemon.run_fingerprinting_add_tasks()
    #     self.db_daemon.run_fingerprinting_add_tasks()
    #
    #     tasks = self.db.get_tasks()
    #     self.assertIsNotNone(tasks)
    #     self.assertEqual(len(tasks), 1)
    #     [self.assertEqual(t.status, 1) for t in tasks]

    def test_run_post_tasks(self):
        self.test_run_fingerprinting_to_add_tasks_repeated_runs()
        tasks = self.db.get_tasks()
        [self.assertIsNone(t.inference_server_response) for t in tasks]
        self.db_daemon.run_post_tasks()
        tasks = self.db.get_tasks()
        [self.assertIsNotNone(t.inference_server_response) for t in tasks]
        [self.assertEqual(t.status, 2) for t in tasks]

    def test_run_get_task(self):
        self.test_run_post_tasks()
        tasks = self.db.get_tasks()
        [self.assertIsNotNone(t.inference_server_response) for t in tasks]
        [self.assertEqual(t.status, 2) for t in tasks]

        self.db_daemon.run_get_tasks()
        tasks = self.db.get_tasks()
        [self.assertIsNotNone(t.inference_server_response) for t in tasks]
        [self.assertEqual(t.status, 3) for t in tasks]

    def test_run_delete_from_inference_server(self):
        scp_test = TestSCP()
        scp_test.setUp()
        try:
            self.test_run_get_task()
            tasks = self.db.get_tasks()
            self.assertNotEqual(0, len(tasks))
            self.db_daemon.run_delete_from_inference_server()

            tasks = self.db.get_tasks()
            self.assertEqual(0, len(tasks))
        except:
            pass
        finally:
            scp_test.tearDown()


if __name__ == '__main__':
    unittest.main()
