import time
from pathlib import Path
import requests
import os

# authentication token that allows you to make requests to the API
API_KEY = os.environ.get('PING_DATA_AUTH_TOKEN')
headers = {"Authorization": f"Token {API_KEY}"}

# example batch payload (simple two-location example)
payload = {
  "locations": [
    {
      "id": "item-1",
      "address": "123 main st, miami, fl",
      "sources": ["PG", "PH"],
    },
    {
      "id": "item-2",
      "address": "456 elm st, los angeles, ca",
      "sources": ["PG", "PH"],
    }
  ],    
  "sources": ["PG", "PH"],
}

API_BASE = "https://data-api.sovfixer.com/api/v1"
# 1. API URL for Start Bulk Enhance Job: https://data-api.sovfixer.com/api/v1/bulk_enhance
start_job_url = f"{API_BASE}/bulk_enhance"
# API response
start_job_response = requests.post(start_job_url, json=payload, headers=headers)

# check response status and record the job ID
if start_job_response.status_code in (200, 201):
	jobid = start_job_response.json()["id"]
	print(start_job_response.json())

else:
	raise RuntimeError
	

## ...

# 2. API URL for Check Bulk Enhance Job Status: https://data-api.sovfixer.com/api/v1/bulk_enhance/{id}
check_job_url = f"{API_BASE}/bulk_enhance/{jobid}"
check_job_response = requests.get(check_job_url, headers=headers)
# ensure response is in a good state
assert check_job_response.status_code in (200, 201)
check_job_json = check_job_response.json()
# Poll every three seconds for job completion
while check_job_json.get("request", {}).get("status") not in ("COMPLETE", "FAILED"):
	print(check_job_json)
	print("Waiting 3 seconds to request again...")
	time.sleep(3)
	check_job_response = requests.get(check_job_url, headers=headers)
	# ensure response is in a good state
	assert check_job_response.status_code in (200, 201)
	check_job_json = check_job_response.json()

print(check_job_json)

# record filenames and urls of the processed outputs
outputs = []
for output in check_job_json.get("result", {}).get("outputs", []):
	outputs.append(
			{
				"filename": output.get("filename"), 
				"url": output.get("url")
			}
		)

## ...
# 3. API URL for Fetch Bulk Enhance Job Result Data: https://data-api.sovfixer.com/api/v1/bulk_enhance/{id}/output/{filename}
for output in outputs:
	fetch_outputs_response = requests.get(output["url"], headers=headers)
	# ensure response is in a good state
	assert fetch_outputs_response.status_code in (200, 201)
	print(f"saving {output['filename']}")
	# save JSON outputs as JSON; others as binary
	out_dir = Path("workflow_example_results")
	out_dir.mkdir(exist_ok=True)
	with open(out_dir / output["filename"], "wb") as outfile:
		outfile.write(fetch_outputs_response.content)    
	print(f"saved {output['filename']}")
