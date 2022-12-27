import json
import logging
import os
import re
from typing import List

from fingerprint_handler.models import Fingerprint, SCU
from models.models import Incoming


class FingerprintHandler:
    def __init__(self, fingerprint_dir):
        self.fingerprint_dir = fingerprint_dir
        self.fingerprints = []
        self.load_fingerprints()

    def load_fingerprints(self):
        for fol, subs, files in os.walk(self.fingerprint_dir):
            for file in files:
                if file.endswith(".json"):
                    file_path = os.path.join(fol, file)
                    try:
                        with open(file_path, "r") as r:
                            fp_dict = json.loads(r.read())
                            fp = Fingerprint(modality_regex=fp_dict["modality_regex"],
                                             sop_class_uid_regex=fp_dict["sop_class_uid_regex"],
                                             study_description_regex=fp_dict["study_description_regex"],
                                             series_description_regex=fp_dict["series_description_regex"],
                                             exclude_regex=fp_dict["exclude_regex"],
                                             inference_server_url=fp_dict["inference_server_url"],
                                             model_human_readable_id=fp_dict["model_human_readable_id"],
                                             scus=[SCU(**scu) for scu in fp_dict["scus"]])
                            self.fingerprints.append(fp)
                    except Exception as e:
                        logging.error(e)

        if len(self.fingerprints) == 0:
            logging.info("No fingerprints found")
        else:
            logging.info(f"Found the following fingerprints:")
            for i, fp in enumerate(self.fingerprints):
                logging.info(f"{str(i)}: {str(fp)}")

    def get_fingerprints(self):
        return self.fingerprints

    def get_fingerprint_from_incoming(self, incoming: Incoming) -> List[Fingerprint]:
        to_return = []  # container for matching fingerprints
        for fingerprint in self.fingerprints:
            ## Start off by checking if include is present in any of the tags.
            exclude_re = re.compile(r"{}".format(fingerprint.exclude_regex), re.IGNORECASE)
            exclude_bool = False
            for tag in [incoming.Modality, incoming.SeriesDescription, incoming.StudyDescription, incoming.SOPClassUID]:
                exclude_bool += bool(exclude_re.search(tag))

            # If exclude_bool has become True, then skip to next fingerprint
            if exclude_bool:
                continue

            # If the code reach this part, any exclude_regex is not in any of the tags.
            # Now look for matching fingerprints.
            modality_re = re.compile(r"{}".format(fingerprint.modality_regex), re.IGNORECASE)
            sop_class_uid_re = re.compile(r"{}".format(fingerprint.sop_class_uid_regex), re.IGNORECASE)
            series_re = re.compile(r"{}".format(fingerprint.series_description_regex), re.IGNORECASE)
            study_re = re.compile(r"{}".format(fingerprint.study_description_regex), re.IGNORECASE)

            # Must match all to be deemed a match
            if modality_re.search(incoming.Modality) and series_re.search(incoming.SeriesDescription) and \
                    study_re.search(incoming.StudyDescription) and sop_class_uid_re.search(incoming.SOPClassUID):
                to_return.append(fingerprint)

        return to_return
