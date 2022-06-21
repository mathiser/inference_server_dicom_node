import json


class DB:
    def __init__(self, scp_json_path):
        self.scp_json_path = scp_json_path
        self.scp_details = []
        with open(self.scp_json_path, "r") as r:
            try:
                self.scp_details = json.loads(r.read())
                print(self.scp_details)
            except Exception as e:
                print(e)

    def get_scp_details(self):
        return self.scp_details
