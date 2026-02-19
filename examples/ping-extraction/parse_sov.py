import time
from pathlib import Path
import requests
import os

# authentication token that allows you to make requests to the API
API_KEY=os.environ.get('SOVFIXER_AUTH_TOKEN')
headers = {"Authorization": f"Token {API_KEY}"}

# file being submitted
file_path = Path("parse_sov_testfile.xlsx")
files = {"file": ("parse_sov_testfile.xlsx", open(file_path, "rb"))}
# request options
payload = {
    # what kind of document is being processed? SOV
    "document_type": "SOV",
    # how should the file be outputted? json, auditor
    "output_formats": ["json", "auditor"],
    # what data integrations should be used? Ping Geocoding, Ping Hazard
    "integrations": ["PG", "PH"]
}

# 1. API URL for Start SOV Parsing Job: https://api.sovfixer.com/api/v1/sov
start_job_url = f"https://api.sovfixer.com/api/v1/sov"
# API response
start_job_response = requests.post(start_job_url, data=payload, files=files, headers=headers)
# check response status and record the SOV ID
if start_job_response.status_code in (200, 201):
    sovid = start_job_response.json()["id"]
else:
    raise RuntimeError

## ... 

# 2. API URL for Check SOV Parsing Job: https://api.sovfixer.com/api/v1/sov/{id}
check_job_url = f"https://api.sovfixer.com/api/v1/sov/{sovid}"
check_job_response = requests.get(check_job_url, headers=headers)
# ensure response is in a good state
assert check_job_response.status_code in (200, 201)
check_job_json = check_job_response.json()
# Poll every three seconds for job completion
while check_job_json["request"]["status"] not in ("COMPLETE", "FAILED"):
    print(check_job_json)
    print("Waiting 3 seconds to request again...")
    time.sleep(3)
    check_job_response = requests.get(check_job_url, headers=headers)
    # ensure response is in a good state
    assert check_job_response.status_code in (200, 201)
    check_job_json = check_job_response.json()

print(check_job_json)

# record filenames and urls of the processed SOV outputs
outputs = []
for output in check_job_json["result"]["outputs"]:
    outputs.append(
            {
                "filename": output["filename"], 
                "url": output["url"]
            }
        )

## ...
# 3. API URL for Fetch Outputs of SOV Parsing Job: https://api.sovfixer.com/api/v1/sov/{id}/output/{filename}
for output in outputs:
    fetch_outputs_response = requests.get(output["url"], headers=headers)
    # ensure response is in a good state
    assert fetch_outputs_response.status_code in (200, 201)
    print(f"saving {output['filename']}")
    output_path = f"workflow_example_results/{output['filename']}"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as outfile:
        outfile.write(fetch_outputs_response.content)    
    print(f"saved {output['filename']}")