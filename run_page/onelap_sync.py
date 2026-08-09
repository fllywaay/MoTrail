# Onelap (顽鹿运动) sync script — rewritten 2026-08 for the new u.onelap.cn API.
# The old www.onelap.cn/api/login + /analysis/list endpoints are dead.
# New flow: POST /api/login -> token, POST /api/otm/ride_record/list -> ids,
# GET /api/otm/ride_record/analysis/{id} -> fileKey,
# GET .../fit_content/{base64(fileKey)} -> real FIT bytes.
# NOTE: .../analysis/fit/{base64} (no "_content") looks similar but actually
# returns a JSON array of per-second telemetry (used for the on-page charts),
# not the binary file — confirmed by manual testing, don't use it here.
# Only the Authorization header is required (no extra cookie needed),
# verified against a manually-downloaded reference file (byte-for-byte match).

import os
import hashlib
import base64
import argparse
import requests
from config import FIT_FOLDER

LOGIN_URL = "https://u.onelap.cn/api/login"
LIST_URL = "https://u.onelap.cn/api/otm/ride_record/list"
ANALYSIS_URL = "https://u.onelap.cn/api/otm/ride_record/analysis/{}"
FIT_URL = "https://u.onelap.cn/api/otm/ride_record/analysis/fit_content/{}"


class Onelap:
    def __init__(self, account, password):
        self.account = account
        self.password = password
        self.token = None
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Origin": "https://u.onelap.cn",
                "Referer": "https://u.onelap.cn/recordPage",
            }
        )

    def login(self):
        pwd_md5 = hashlib.md5(self.password.encode()).hexdigest()
        r = self.session.post(
            LOGIN_URL, json={"account": self.account, "password": pwd_md5}
        )
        r.raise_for_status()
        result = r.json()
        data = result.get("data")
        if not data:
            raise RuntimeError(f"Login failed: {result}")
        self.token = data[0]["token"]
        self.session.headers.update({"Authorization": self.token})
        print("Logged in.")

    def get_activities(self, page_size=100):
        activities = []
        page = 1
        while True:
            r = self.session.post(
                LIST_URL, json={"page": page, "limit": page_size}
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
        r = self.session.get(ANALYSIS_URL.format(record_id))
        r.raise_for_status()
        result = r.json()
        record = result.get("data", {}).get("ridingRecord", {})
        return record.get("fileKey")

    def download_fit(self, file_key):
        encoded = base64.b64encode(file_key.encode()).decode()
        r = self.session.get(FIT_URL.format(encoded))
        r.raise_for_status()
        content = r.content
        # A real FIT file has ".FIT" as an ASCII marker at byte offset 8-11.
        # If it's not there, we almost certainly got an error page/JSON back
        # instead of the binary file — surface that instead of writing garbage.
        if len(content) < 12 or content[8:12] != b".FIT":
            preview = content[:200]
            raise RuntimeError(
                f"Downloaded content for {file_key} doesn't look like a FIT "
                f"file (content-type={r.headers.get('Content-Type')}, "
                f"first bytes={preview!r})"
            )
        return content

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
            try:
                content = self.download_fit(file_key)
            except RuntimeError as e:
                print(f"failed to download {record_id}: {e}")
                continue
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
