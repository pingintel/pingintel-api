import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from pingintel_api.pingvision import types as t

POLL_INTERVAL = 15  # seconds


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
team = teams[0]  # Select team by index, or filter by team_name/company_name
team_uuid = team["team_uuid"]
division_uuid = team["division_uuid"]
status_uuids = {s["name"]: s["uuid"] for s in team.get("statuses", [])}

## ...

# 2. Create Submission
# https://docs.pingintel.com/ping-vision/create-submission/initiate-new-submission
payload = {
    "client_ref": "my_salesforce_id",  # Optional: external reference ID
    "insured_name": "Acme Corp",  # Optional: insured name
    "team_uuid": team_uuid,  # Required: team ID
}

create_submission_url = f"{BASE_URL}/submission"
create_submission_response = requests.post(create_submission_url, data=payload, files=files, headers=headers)
if create_submission_response.status_code not in (200, 201):
    raise RuntimeError(f"Failed to create submission: {create_submission_response.status_code}")

submission_id = create_submission_response.json()["id"]
print(f"Created submission: {color_text(submission_id, 'green')}")

## ...

# 3. Poll for Status Changes via List Submission Events
# https://docs.pingintel.com/ping-vision/get-submission-data/list-submission-events
earliest_allowed_time = datetime.now(timezone.utc)
last_cursor_id = None
current_status = None
submission_events_url = f"{BASE_URL}/submission-events"
submission_activity_url = f"{BASE_URL}/submission"

print(f"Polling for status changes on submission {color_text(submission_id, 'yellow')}...")
while True:
    events_params = {
        "pingid": submission_id,
        "start": earliest_allowed_time.strftime("%Y%m%d%H%M%S"),
        "page_size": 50,
        "team": team_uuid,
        "division": division_uuid,
    }
    if last_cursor_id:
        events_params["cursor_id"] = last_cursor_id

    events_response = requests.get(submission_events_url, params=events_params, headers=headers)
    if events_response.status_code not in (200, 201):
        print(color_text(f"Error polling events: {events_response.status_code}", "red"))
        time.sleep(POLL_INTERVAL)
        continue

    events_json = events_response.json()
    last_cursor_id = events_json.get("cursor_id")

    # Process status change events
    for event in events_json.get("results", []):
        if event.get("event_type") == t.SUBMISSION_EVENT_LOG_TYPE.SUBMISSION_STATUS_CHANGE:
            old_status = event.get("old_value", "")
            new_status = event.get("new_value", "")
            print(
                color_text(f"Status change: {event.get('message', '')}", "green"),
                old_status,
                "->",
                new_status,
            )
            current_status = new_status

    # 4. Change Submission Status
    # https://docs.pingintel.com/ping-vision/update-submission/change-submission-status
    change_status_url = f"{BASE_URL}/submission/{submission_id}/change_status"

    if current_status == status_uuids.get("Pending Clearance"):
        # In a real workflow, the clearance team would evaluate the submission
        # for factors like incumbents or duplicate submissions from other brokerages.
        # For this example, we will just automatically clear it to demonstrate the workflow.
        print(color_text("Changing status to Cleared...", "yellow"))
        response = requests.patch(
            change_status_url,
            json={"workflow_status_uuid": status_uuids["Cleared"]},
            headers=headers,
        )
        if response.status_code not in (200, 201):
            raise RuntimeError(f"Failed to change status: {response.status_code}")
        print(color_text("Status changed to: Cleared", "green"))

    if current_status == status_uuids.get("Cleared"):
        # In a real workflow, this transition happens when the DTI (Days To Inception) date
        # is reached, or when manually requested to begin the scrubbing/data entry process.
        # For this example, we will just automatically move it to Data Entry to demonstrate the workflow.
        print(color_text("Changing status to Data Entry...", "yellow"))
        response = requests.patch(
            change_status_url,
            json={"workflow_status_uuid": status_uuids["Data Entry"]},
            headers=headers,
        )
        if response.status_code not in (200, 201):
            raise RuntimeError(f"Failed to change status: {response.status_code}")
        print(color_text("Status changed to: Data Entry", "green"))
        break

    time.sleep(POLL_INTERVAL)
    current_status_name = next((k for k, v in status_uuids.items() if v == current_status), None)
    print(f"Waiting... (current status: {color_text(current_status_name, 'yellow')})")

## ...

# 5. Download Scrubber for Human Certification
# https://docs.pingintel.com/ping-vision/get-submission-data/list-recent-submission-activity
print(color_text("\nPress enter to download the scrubber for certification.", "red"))
input("> ")

activity_params = {
    "id": submission_id,
    "page_size": 1,
    "team_uuid": team_uuid,
    "division_uuid": division_uuid,
}
activity_response = requests.get(submission_activity_url, params=activity_params, headers=headers)
if activity_response.status_code not in (200, 201):
    raise RuntimeError(f"Failed to get submission activity: {activity_response.status_code}")

activity_json = activity_response.json()
submission_data = activity_json.get("results", [])[0]
documents = submission_data.get("documents", [])

scrubber_doc = None
for doc in documents:
    if doc.get("document_type") == "SOVFIXER_SCRUBBER":
        scrubber_doc = doc
        break
if not scrubber_doc:
    raise RuntimeError("Scrubber document not found")

scrubber_filename = f"{submission_id}_{scrubber_doc['filename']}"
scrubber_response = requests.get(scrubber_doc["url"], headers=headers)
if scrubber_response.status_code not in (200, 201):
    raise RuntimeError(f"Failed to download scrubber: {scrubber_response.status_code}")

with open(scrubber_filename, "wb") as f:
    f.write(scrubber_response.content)
print(color_text(f"Downloaded scrubber to: {scrubber_filename}", "green"))
print(
    color_text(
        "Open in Excel and certify the scrubber in the Ping menu, then return here.",
        "yellow",
    )
)

## ...

# 6. After downloading the scrubber, open it in Excel. Use the Ping menu in Excel to review the extracted data and certify the submission.

## ...

# 7. Wait for Underwriting Status (Human Certification Complete)
print(color_text("\nWaiting for human certification (Underwriting status)...", "yellow"))

while True:
    events_params = {
        "pingid": submission_id,
        "start": earliest_allowed_time.strftime("%Y%m%d%H%M%S"),
        "page_size": 50,
        "team": team_uuid,
        "division": division_uuid,
    }
    if last_cursor_id:
        events_params["cursor_id"] = last_cursor_id

    events_response = requests.get(submission_events_url, params=events_params, headers=headers)
    if events_response.status_code not in (200, 201):
        print(color_text(f"Error polling events: {events_response.status_code}", "red"))
        time.sleep(POLL_INTERVAL)
        continue

    events_json = events_response.json()
    last_cursor_id = events_json.get("cursor_id")

    for event in events_json.get("results", []):
        if event.get("event_type") == t.SUBMISSION_EVENT_LOG_TYPE.SUBMISSION_STATUS_CHANGE:
            print(color_text(f"Status change: {event.get('message', '')}", "green"))
            current_status = event.get("new_value", "")

    if current_status == status_uuids.get("Underwriting"):
        print(color_text("Certification complete. Underwriting status reached.", "green"))
        break

    time.sleep(POLL_INTERVAL)
    current_status_name = next((k for k, v in status_uuids.items() if v == current_status), None)
    print(f"Waiting for certification... (current status: {color_text(current_status_name or 'unknown', 'yellow')})")

## ...

# 8. Wait for the RUN_OUTPUTTERS job to complete
print(color_text("Waiting for final outputs...", "yellow"))
while True:
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
        time.sleep(POLL_INTERVAL)
        continue

    submission = results[0]
    jobs = submission.get("jobs", [])
    outputters_job = next((j for j in jobs if j.get("job_type") == "RUN_OUTPUTTERS"), None)

    if outputters_job and outputters_job.get("processing_pct_complete") == 100:
        print(color_text("Final outputs ready for download.", "green"))
        break

    time.sleep(POLL_INTERVAL)

## ...

# 9. Download Final Output Documents
# https://docs.pingintel.com/ping-vision/get-submission-data/download-submission-document
os.makedirs("workflow_example_results", exist_ok=True)

for doc in submission.get("documents", []):
    doc_type = doc.get("document_type", "")
    filename = doc.get("filename", "")

    if doc_type in ["SOVFIXER_OUTPUT", "SOVFIXER_JSON"] and not doc.get("is_archived", False):
        download_url = f"{BASE_URL}/submission/{submission_id}/document/{filename}"
        download_response = requests.get(download_url, headers=headers)
        if download_response.status_code not in (200, 201):
            raise RuntimeError(f"Failed to download {filename}: {download_response.status_code}")

        output_path = f"workflow_example_results/{submission_id}_{filename}"
        with open(output_path, "wb") as outfile:
            outfile.write(download_response.content)
        print(color_text(f"Saved {doc_type}: {output_path}", "green"))

print(color_text(f"\nWorkflow complete for submission {submission_id}", "green"))

##
