"""
Update an SOV workflow demo.

Run with: python update_sov.py

Requires a corrections.csv in the working directory.
Each row must identify the target building using item_key
or both sheet_name and sheet_row_number.
"""

import os
import time

import requests

API_KEY = os.environ.get("SOVFIXER_AUTH_TOKEN")
BASE_URL = "https://api.sovfixer.com/api/v1"

SOVID = "s-no-ping-hggcsk"
LOCATIONS_CSV = "corrections.csv"
EXTRA_DATA = {"insured_name": "Acme Corp"}  # policy-level fields to carry into output
OUTPUT_FORMATS = ["json"]
POLL_SECONDS = 3

headers = {"Authorization": f"Token {API_KEY}"}


# 1. Initiate the update job
resp = requests.post(
    f"{BASE_URL}/sov/{SOVID}/initiate_update",
    headers=headers,
)
print(resp.json())
resp.raise_for_status()
UPDATE_ID = resp.json()["id"]
print("initiated update job:", UPDATE_ID)


# 2. Add locations from CSV
with open(LOCATIONS_CSV, "rb") as f:
    resp = requests.post(
        f"{BASE_URL}/sov/update/{UPDATE_ID}/add_locations",
        files={"file": (LOCATIONS_CSV, f)},
        headers=headers,
    )
print(resp.json())
resp.raise_for_status()


# 3. Start the job. extra_data carries policy-level fields into the output
resp = requests.post(
    f"{BASE_URL}/sov/update/{UPDATE_ID}/start",
    json={"extra_data": EXTRA_DATA, "output_formats": OUTPUT_FORMATS},
    headers=headers,
)
print(resp.json())
resp.raise_for_status()


# 4. Poll until the job reaches a terminal state
status_url = f"{BASE_URL}/sov/update/{UPDATE_ID}"
response_json = requests.get(status_url, headers=headers).json()

while response_json["request"]["status"] not in ("COMPLETE", "FAILED"):
    print(response_json)
    print("Waiting 3 seconds to request again...")
    time.sleep(POLL_SECONDS)
    response_json = requests.get(status_url, headers=headers).json()

print(response_json)
print("final status:", response_json["request"]["status"])


# 5. Download outputs
for out in response_json.get("result", {}).get("outputs", []):
    print(f"saving {out['filename']}")
    r = requests.get(out["url"], headers=headers)
    r.raise_for_status()
    with open(out["filename"], "wb") as f:
        f.write(r.content)
    print(f"saved {out['filename']}")
