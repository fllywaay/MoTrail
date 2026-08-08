# Onelap (顽鹿运动) sync script — rewritten 2026-08 for the new u.onelap.cn API.
# The old www.onelap.cn/api/login + /analysis/list endpoints are dead.
# New flow: POST /api/login -> token, POST /api/otm/ride_record/list -> ids,
# GET /api/otm/ride_record/analysis/{id} -> fileKey, GET .../fit/{base64(fileKey)} -> FIT bytes.

import os
import hashlib
import base64
import argparse
import requests
from config import FIT_FOLDER

LOGIN_URL = "https://u.onelap.cn/api/login"
LIST_URL = "https://u.onelap.cn/api/otm/ride_record/list"
ANALYSIS_URL = "https://u.onelap.cn/api/otm/ride_record/analysis/{}"
FIT_URL = "https://u.onelap.cn/api/otm/ride_record/analysis/fit/{}"


class Onelap:
    def __init__(self, account, password):
        self.account = account
        self.password = password
        self.token = None

    def login(self):
        pwd_md5 = hashlib.md5(self.password.encode()).hexdigest()
        r = requests.post(
            LOGIN_URL, json={"account": self.account, "password": pwd_md5}
        )
        r.raise_for_status()
        result = r.json()
        data = result.get("data")
        if not data:
            raise RuntimeError(f"Login failed: {result}")
        self.token = data[0]["token"]
        print("Logged in.")

    def _headers(self):
        return {"Authorization": self.token}

    def get_activities(self, page_size=100):
        activities = []
        page = 1
        while True:
            r = requests.post(
                LIST_URL,
                headers=self._headers(),
                json={"page": page, "limit": page_size},
            )
            r.raise_for_status()
            result = r.json()
            items = result.get("data", {}).get("list", [])
            if not items:
                break
            activities.extend(items)
            if len(items) < page_size:
                break
            page += 1
        return activities

    def get_file_key(self, record_id):
        r = requests.get(ANALYSIS_URL.format(record_id), headers=self._headers())
        r.raise_for_status()
        result = r.json()
        record = result.get("data", {}).get("ridingRecord", {})
        return record.get("fileKey")

    def download_fit(self, file_key):
        encoded = base64.b64encode(file_key.encode()).decode()
        r = requests.get(FIT_URL.format(encoded), headers=self._headers())
        r.raise_for_status()
        return r.content

    def download_onelap_data(self):
        os.makedirs(FIT_FOLDER, exist_ok=True)
        activities = self.get_activities()
        print(f"Found {len(activities)} activities")
        for activity in activities:
            record_id = activity.get("id")
            if not record_id:
                continue
            file_path = os.path.join(FIT_FOLDER, f"{record_id}.fit")
            if os.path.exists(file_path):
                print(f"{record_id}.fit already exists, skipped")
                continue
            file_key = self.get_file_key(record_id)
            if not file_key:
                print(f"no fileKey for {record_id}, skipped")
                continue
            content = self.download_fit(file_key)
            with open(file_path, "wb") as f:
                f.write(content)
            print(f"downloaded {record_id}.fit")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("account", help="Onelap account (phone/email)")
    parser.add_argument("password", help="Onelap password")
    parser.add_argument(
        "--with-fit",
        dest="with_fit",
        action="store_true",
        help="get all Onelap data to fit and download",
    )
    options = parser.parse_args()

    onelap = Onelap(options.account, options.password)
    onelap.login()
    onelap.download_onelap_data()
