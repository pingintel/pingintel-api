import os
import time
from pathlib import Path

import requests
from pingintel_api.pingvision import types as t

POLL_INTERVAL = 10  # seconds


def color_text(text: str, color: str) -> str:
    """Wrap text in ANSI color codes for terminal output."""
    colors = {"red": "\033[31m", "yellow": "\033[33m", "green": "\033[32m"}
    if color not in colors:
        return text
    reset = "\033[0m"
    return f"{colors[color]}{text}{reset}"


# Configuration
API_KEY = os.environ.get("PINGVISION_AUTH_TOKEN")
BASE_URL = "https://vision.pingintel.com/api/v1"
headers = {"Authorization": f"Token {API_KEY}"}

# File to submit
file_path = Path("demo_email.eml")

files = [("files", (file_path.name, open(file_path, "rb")))]

## ...

# 1. List User Teams
# https://docs.pingintel.com/ping-vision/user-memberships/list-user-teams
list_teams_url = f"{BASE_URL}/user/teams/"
list_teams_response = requests.get(list_teams_url, headers=headers)
if list_teams_response.status_code not in (200, 201):
    raise RuntimeError(f"Failed to list teams: {list_teams_response.status_code}")

teams = list_teams_response.json()
# select team by team_uuid or division_uuid
team = teams[0]
team_uuid = team["team_uuid"]  # Unique identifier for the team
division_uuid = team["division_uuid"]  # Division within the team

# Build a mapping of workflow status names to UUIDs for later use
status_uuids = {s["name"]: s["uuid"] for s in team.get("statuses", [])}

## ...

# Step 2. Create Submission
# https://docs.pingintel.com/ping-vision/create-submission/initiate-new-submission

payload = {
    "client_ref": "my_salesforce_id",  # Optional: your external reference ID
    "insured_name": "Acme Corp",  # Optional: name of the insured party
    "team_uuid": team_uuid,  # Required: which team should receive this submission
}

create_submission_url = f"{BASE_URL}/submission"
create_submission_response = requests.post(create_submission_url, data=payload, files=files, headers=headers)
if create_submission_response.status_code not in (200, 201):
    raise RuntimeError(f"Failed to create submission: {create_submission_response.status_code}")

submission_id = create_submission_response.json()["id"]
print(f"Created submission: {color_text(submission_id, 'green')}")

## ...

# Step 3. Poll for Job Completion

submission_activity_url = f"{BASE_URL}/submission"

print(color_text("Polling for jobs to complete...", "yellow"))

# track completed jobs
completed_jobs = set()

while True:
    # Query for the specific submission by ID
    activity_params = {
        "id": submission_id,
        "page_size": 1,
        "team_uuid": team_uuid,
        "division_uuid": division_uuid,
    }
    activity_response = requests.get(submission_activity_url, params=activity_params, headers=headers)

    if activity_response.status_code not in (200, 201):
        print(color_text(f"Error checking activity: {activity_response.status_code}", "red"))
        time.sleep(POLL_INTERVAL)
        continue

    results = activity_response.json().get("results", [])
    if not results:
        print(color_text("Waiting for submission data...", "yellow"))
        time.sleep(POLL_INTERVAL)
        continue

    submission = results[0]
    jobs = submission.get("jobs", [])

    # Display progress for each job
    for j in jobs:
        job_id = j.get("job_id")
        job_type = j.get("job_type", "UNKNOWN")  # e.g., "SOVFIXER", "RUN_OUTPUTTERS"
        pct = j.get("processing_pct_complete", 0)
        status = j.get("processing_status", "?")
        message = j.get("processing_last_message", "")  # Human-readable status message

        if status == "C" and job_id not in completed_jobs:
            # job completed
            print(color_text(f"✓ {job_type}: {pct:.0f}% - {message}", "green"))
            completed_jobs.add(job_id)
        elif status != "C" and job_id not in completed_jobs:
            # job still in progress
            print(color_text(f"⋯ {job_type}: {pct:.0f}% - {message}", "yellow"))

    # Check if the final outputters job is complete
    outputters_job = next((j for j in jobs if j.get("job_type") == "RUN_OUTPUTTERS"), None)

    if outputters_job and outputters_job.get("processing_pct_complete") == 100:
        print(color_text("Final outputs ready for download.", "green"))
        break

    time.sleep(POLL_INTERVAL)

## ...

# Step 4. Download Final Output Documents
# https://docs.pingintel.com/ping-vision/get-submission-data/download-submission-document

os.makedirs("workflow_example_results", exist_ok=True)

for doc in submission.get("documents", []):
    doc_type = doc.get("document_type", "")
    filename = doc.get("filename", "")

    # Download only the final output files
    if doc_type in ["SOVFIXER_OUTPUT", "SOVFIXER_JSON"] and not doc.get("is_archived", False):
        download_url = f"{BASE_URL}/submission/{submission_id}/document/{filename}"
        download_response = requests.get(download_url, headers=headers)

        if download_response.status_code not in (200, 201):
            raise RuntimeError(f"Failed to download {filename}: {download_response.status_code}")

        # Save with submission ID prefix to avoid filename collisions
        output_path = f"workflow_example_results/{submission_id}_{filename}"
        with open(output_path, "wb") as outfile:
            outfile.write(download_response.content)
        print(color_text(f"Saved {doc_type}: {output_path}", "green"))

print(color_text(f"\nWorkflow complete for submission {submission_id}", "green"))

##
