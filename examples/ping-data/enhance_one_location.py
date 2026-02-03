import requests
import json
from pathlib import Path
import os

# authentication token that allows you to make requests to the API
API_KEY = os.environ.get('PING_DATA_AUTH_TOKEN')
headers = {"Authorization": f"Token {API_KEY}"}

# single-address example
params = {
    "address": "1600 pennsylvania ave nw washington dc 20500",
    "sources": ["PG", "PH"]
}

API_BASE = "https://data-api.sovfixer.com/api/v1"
url = f"{API_BASE}/enhance"
# 1. API URL for Enhance Location: https://data-api.sovfixer.com/api/v1/enhance
enhance_location_response = requests.get(url, headers=headers, params=params)
# check response status
if enhance_location_response.status_code not in (200, 201):
    print("Error:", enhance_location_response.status_code, enhance_location_response.text)
    raise Exception("Error enhancing location")

data = enhance_location_response.json()
# print first 100 characters of result
print(json.dumps(data, indent=2)[:100])

# save result
out_dir = Path("workflow_example_results")
out_dir.mkdir(exist_ok=True)
print("saving enhanced location result...")
with open(out_dir / "enhanced_location.json", "w") as fh:
    json.dump(data, fh, indent=2)
print('saved', out_dir / "enhanced_location.json")