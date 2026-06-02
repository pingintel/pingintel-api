"""Demo: request and download an output for an existing SOV.

Two IDs are involved. Keep them separate:
  - SOVID: identifies the parsed SOV, passed in the POST path.
  - request_id: returned by the POST under request.id, used to poll the GET.
"""

import os
import time
import requests

BASE_URL = "https://api.sovfixer.com/api/v1"
SOVID = "s-no-ping-hggcsk"  # SOV ID from a previously completed parsing job
OUTPUT_FORMAT = "json"  # desired output format, e.g., json or auditor
POLL_SECONDS = 3

API_KEY = os.environ.get("SOVFIXER_AUTH_TOKEN")
headers = {"Authorization": f"Token {API_KEY}"}

# 1. Request the output. If a cached output is available the response
#    returns COMPLETE immediately. Otherwise, generation begins and we
#    receive a request.id to poll.

start_url = f"{BASE_URL}/sov/{SOVID}/get_or_create_output"
payload = {"output_format": OUTPUT_FORMAT, "revision": -1, "overwrite_existing": False}
start_json = requests.post(start_url, json=payload, headers=headers).json()
request_id = start_json["request"]["id"]


# 2. Poll until the output is ready. request_id is the polling ID — not SOVID.
check_url = f"{BASE_URL}/sov/get_or_create_output/{request_id}"
check_json = start_json
while check_json["request"]["status"] not in ("COMPLETE", "FAILED"):
    time.sleep(POLL_SECONDS)
    check_json = requests.get(check_url, headers=headers).json()

if check_json["request"]["status"] == "FAILED":
    raise RuntimeError(f"Output generation failed: {check_json}")

# 3. Download the file. result.url serves the output in its native format,
#    so write the response body as binary.
result = check_json["result"]
download = requests.get(result["url"], headers=headers)
os.makedirs("workflow_example_results", exist_ok=True)
with open(f"workflow_example_results/{result['scrubbed_filename']}", "wb") as f:
    f.write(download.content)
print(f"saved {result['scrubbed_filename']}")
