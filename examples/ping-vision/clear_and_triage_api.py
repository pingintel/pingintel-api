"""
PingVision Clearance & Triage Workflow — Raw API Example

This script demonstrates an end-to-end clearance workflow using direct HTTP requests
to the PingVision API. It uploads a submission (.eml file), monitors status changes
via polling, programmatically advances the submission through clearance stages,
waits for human certification, and finally downloads the finished SOV Fixer outputs.

This is the "raw requests" version of pingvision_clear_and_triage.py, intended to
show exactly what HTTP calls are being made without the abstraction of the
pingintel_api client library.

Prerequisites:
  - A valid PingVision API auth token set in PINGVISION_AUTH_TOKEN_LOCAL environment variable
  - Network access to the PingVision instance at the configured BASE_URL
  - An .eml file containing the submission you want to process

Usage:
  python clear_and_triage_api.py --eml /path/to/submission.eml --company "Acme Corp" --team "Acme Corp"
  python clear_and_triage_api.py --eml demo_email.eml --company "Ping Intel" --team "Ping Intel" --api-url "http://localhost:8002"
"""

import argparse
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

# How often to poll for status changes (in seconds)
POLL_INTERVAL = 15

# Shared state dictionary for tracking submission statuses across threads
# Maps pingid -> current status UUID
db: dict[str, str] = {}


def color_text(text: str, color: str) -> str:
    """
    Wrap *text* in ANSI escape codes so it renders in the given *color* when
    printed to a terminal.

    Supported colors: "red", "yellow", "green". If an unsupported color is
    passed the text is returned unmodified.
    """
    colors = {"red": "\033[31m", "yellow": "\033[33m", "green": "\033[32m"}
    if color not in colors:
        return text
    reset = "\033[0m"
    return f"{colors[color]}{text}{reset}"


def authenticate(api_url: str, auth_token: str) -> dict:
    """
    Authenticate to the PingVision API and return the necessary headers and base URL.
    """
    if auth_token is None:
        auth_token = os.environ.get("PINGVISION_AUTH_TOKEN_LOCAL")
    if not auth_token:
        raise RuntimeError("No auth token provided. Set PINGVISION_AUTH_TOKEN_LOCAL or pass --auth-token")

    base_url = api_url.rstrip("/")
    if not base_url.endswith("/api/v1"):
        base_url = f"{base_url}/api/v1"

    headers = {"Authorization": f"Token {auth_token}"}
    return headers, base_url


def get_team(base_url: str, headers: dict, company_name: str, team_name: str) -> dict:
    """
    Look up a PingVision team by its company and team display names.

    This calls the PingVision list_teams endpoint and searches for an exact
    match on both company_name and team_name. Use it early in your workflow
    to obtain the team_uuid and division_uuid you'll need for submission
    creation and status lookups.

    If the team is not found, all available teams are printed to the console
    to help you identify the correct names, and a RuntimeError is raised.
    """
    list_teams_url = f"{base_url}/user/teams/"
    response = requests.get(list_teams_url, headers=headers)
    if response.status_code not in (200, 201):
        raise RuntimeError(f"Failed to list teams: {response.status_code}")

    teams = response.json()
    for team in teams:
        if team["company_name"] == company_name and team["team_name"] == team_name:
            return team

    print("Available teams:")
    for team in teams:
        print(f"  * {team['company_name']} / {team['team_name']} ({team['team_uuid']})")
    raise RuntimeError(f"Team not found: {company_name} / {team_name}")


def get_statuses(base_url: str, headers: dict, division_uuid: str) -> dict[str, str]:
    """
    Retrieve the workflow statuses configured for a division and return as a name->uuid mapping.

    This calls the list_submission_statuses endpoint to get all available workflow
    statuses (e.g., "Received", "Pending Clearance", "Cleared", "Data Entry", etc.).

    Returns a dict mapping status names to their UUIDs for easy lookup when
    transitioning submissions between stages.
    """
    statuses_url = f"{base_url}/submission-status"
    params = {"division": division_uuid}
    response = requests.get(statuses_url, params=params, headers=headers)
    if response.status_code not in (200, 201):
        raise RuntimeError(f"Failed to list statuses: {response.status_code}")

    statuses = response.json()
    return {s["name"]: s["uuid"] for s in statuses}


def create_submission(
    base_url: str,
    headers: dict,
    team_uuid: str,
    file_path: str,
    insured_name: str = "Acme Corp",
    client_ref: str = None,
) -> str:
    """
    Upload files to create a new submission.
    Returns the pingid of the created submission.
    """
    with open(file_path, "rb") as eml_file:
        files = [("files", (Path(file_path).name, eml_file))]
        payload = {
            "team_uuid": team_uuid,
            "insured_name": insured_name,
        }
        if client_ref:
            payload["client_ref"] = client_ref
        create_submission_url = f"{base_url}/submission"
        response = requests.post(create_submission_url, data=payload, files=files, headers=headers)
    if response.status_code not in (200, 201):
        raise RuntimeError(f"Failed to create submission: {response.status_code}")

    return response.json()["id"]


# =============================================================================
# Background Event Monitor (USER ACTION)
# =============================================================================
# Poll for submission status changes. In production, this polling typically
# runs as a background process watching ALL submissions for your team/division.
# This demo filters to a single pingid for clarity and to show clear
# cause-and-effect in the console output.
# =============================================================================
def poll_submission_events(
    base_url: str,
    headers: dict,
    division_uuid: str,
    team_uuid: str,
    pingid: str,
    earliest_allowed_time: datetime,
):
    """
    Background polling loop that watches for submission status-change events.

    This function is meant to be run in a daemon thread. It calls the
    list_submission_events endpoint every POLL_INTERVAL seconds and updates
    the shared *db* dict with the latest status UUID for the pingid it sees.

    Status-change events are printed to the console as they arrive so you
    can observe the submission progressing through the workflow in real time.

    Note: This demo polls for a single pingid for clarity. In production, you
    would omit the pingid filter and track all submissions, potentially routing
    events to different handlers or queues based on the submission's pingid.
    """
    submission_events_url = f"{base_url}/submission-events"
    last_cursor_id = None

    while True:
        time.sleep(POLL_INTERVAL)
        try:
            events_params = {
                "pingid": pingid,
                "start": earliest_allowed_time.strftime("%Y%m%d%H%M%S"),
                "page_size": 50,
                "team": team_uuid,
                "division": division_uuid,
            }
            if last_cursor_id:
                events_params["cursor_id"] = last_cursor_id

            response = requests.get(submission_events_url, params=events_params, headers=headers)
            if response.status_code not in (200, 201):
                print(color_text(f"Error polling events: {response.status_code}", "red"))
                continue

            events_json = response.json()
            last_cursor_id = events_json.get("cursor_id")

            for event in events_json.get("results", []):
                if event.get("event_type") == "SSC":  # Submission Status Change
                    new_status = event.get("new_value", "")
                    db[pingid] = new_status
                    print(
                        color_text(f"Status change: {event.get('message', '')}", "green"),
                        event.get("old_value", ""),
                        "->",
                        new_status,
                    )
        except Exception as e:
            print(color_text(f"Error in event polling: {e}", "red"))


def wait_for_status(
    pingid: str,
    desired_status: str,
    status_uuids: dict[str, str],
    timeout: int = 600,
):
    """
    Block until the submission identified by *pingid* reaches *desired_status*.

    This polls the shared *db* dict (populated by poll_submission_events) and
    compares the current status UUID against the UUID of *desired_status*.
    Progress is printed to the console every 6 seconds.
    """
    desired_status_uuid = status_uuids.get(desired_status)
    start = time.time()

    while time.time() - start < timeout:
        status_uuid = db.get(pingid)
        if status_uuid == desired_status_uuid:
            print(color_text(f"Status for {pingid} reached: {desired_status}", "green"))
            return

        current_status_name = next((k for k, v in status_uuids.items() if v == status_uuid), "unknown")
        print(
            f"Waiting for {pingid} to reach {color_text(desired_status, 'green')} "
            f"(current: {color_text(current_status_name, 'yellow')})"
        )
        time.sleep(6)

    raise TimeoutError(f"Timed out waiting for {pingid} to reach '{desired_status}' after {timeout}s")


def wait_for_job(
    base_url: str,
    headers: dict,
    pingid: str,
    team_uuid: str,
    division_uuid: str,
    job_type: str,
    timeout: int = 300,
    interval: int = 3,
) -> dict:
    """
    Block until a specific background job on a submission completes.

    Polls the list_submission_activity endpoint and checks whether the job
    identified by *job_type* (e.g., "RUN_OUTPUTTERS") has reached 100%
    completion. Returns the full submission data once the job finishes,
    which includes the documents list you can use to download outputs.
    """
    submission_activity_url = f"{base_url}/submission"
    start = time.time()

    while time.time() - start < timeout:
        activity_params = {
            "id": pingid,
            "page_size": 1,
            "team_uuid": team_uuid,
            "division_uuid": division_uuid,
        }
        response = requests.get(submission_activity_url, params=activity_params, headers=headers)

        if response.status_code not in (200, 201):
            print(color_text(f"Error checking activity: {response.status_code}", "red"))
            time.sleep(interval)
            continue

        results = response.json().get("results", [])
        if not results:
            time.sleep(interval)
            continue

        submission = results[0]
        jobs = submission.get("jobs", [])
        job = next((j for j in jobs if j.get("job_type") == job_type), None)

        if job:
            pct = job.get("processing_pct_complete", 0)
            message = job.get("processing_last_message", "")
            print(color_text(f"⋯ {job_type}: {pct:.0f}% - {message}", "yellow"))

            if pct == 100:
                print(color_text(f"✓ {job_type} complete", "green"))
                return submission

        time.sleep(interval)

    raise TimeoutError(f"{job_type} did not complete within {timeout}s")


def change_status(base_url: str, headers: dict, pingid: str, new_status_uuid: str):
    """
    Change the workflow status of a submission.

    Calls the change_status endpoint to transition the submission to a new
    workflow stage. Use this to programmatically advance submissions through
    clearance, data entry, underwriting, etc.
    """
    change_status_url = f"{base_url}/submission/{pingid}/change_status"
    response = requests.patch(
        change_status_url,
        json={"workflow_status_uuid": new_status_uuid},
        headers=headers,
    )
    if response.status_code not in (200, 201):
        raise RuntimeError(f"Failed to change status: {response.status_code}")


def update_submission(base_url: str, headers: dict, pingid: str, attr_to_update: str, value):
    """
    Update a property of the submission.

        This is a critical step in the clearance workflow. When is_building_data_ready
        is set to True, it signals that:
          - The SOV data has been parsed and validated
          - Addresses have been geocoded
          - Third-party enrichment data has been attached
          - The submission is ready for underwriting review

        In production, this flag is typically set automatically by Ping's certification
        process after a human reviewer has verified the data quality. For demo/testing
        purposes, this can be set programmatically to advance the workflow.

        This triggers the RUN_OUTPUTTERS job which generates the final output files.
    """
    update_submission_url = f"{base_url}/submission/{pingid}"
    response = requests.patch(
        update_submission_url,
        json={attr_to_update: value},
        headers=headers,
    )
    if response.status_code not in (200, 201):
        raise RuntimeError(f"Failed to update submission: {response.status_code}")


def download_document(base_url: str, headers: dict, pingid: str, filename: str, output_path: str):
    """
    Download a document from a submission.

    Fetches the document content and writes it to *output_path*.
    """
    download_url = f"{base_url}/submission/{pingid}/document/{filename}"
    response = requests.get(download_url, headers=headers)
    if response.status_code not in (200, 201):
        raise RuntimeError(f"Failed to download {filename}: {response.status_code}")

    with open(output_path, "wb") as f:
        f.write(response.content)


def run_clearance_workflow(
    *,
    eml_path: str,
    company_name: str,
    team_name: str,
    api_url: str = "http://localhost:8002/api/v1",
    auth_token: str | None = None,
) -> str:
    """
    Execute the full clearance workflow for a single .eml submission.

    This is the main entry point. It performs the following steps:

      1. Resolves the team and division from PingVision.
      2. Uploads the .eml file as a new submission (USER ACTION).
      3. Starts a background thread to monitor status-change events (USER ACTION).
      4. Waits for "Pending Clearance", advances to "Cleared" and "Data Entry" (PING).
      5. Ping certifies data (PING - demo simplifies via Update Submission API).
      6. Waits for "Underwriting" status (USER ACTION polling).
      7. Waits for the RUN_OUTPUTTERS job to finish (PING).
      8. Downloads the SOVFIXER_JSON document (USER ACTION).

    Returns the pingid of the created submission.
    """
    # Setup API authentication and base URL
    headers, base_url = authenticate(api_url, auth_token)

    # ==========================================================================
    # Step 1: Get Team and Statuses
    # ==========================================================================
    print(color_text("Step 1: Looking up team and workflow statuses...", "yellow"))

    team = get_team(base_url, headers, company_name, team_name)
    team_uuid = team["team_uuid"]
    division_uuid = team["division_uuid"]
    print(f"  Team: {team['team_name']} ({team_uuid})")

    status_uuids = get_statuses(base_url, headers, division_uuid)
    print(f"  Found {len(status_uuids)} workflow statuses")

    # ==========================================================================
    # Step 2: Create Submission
    # ==========================================================================
    # USER ACTION: A broker or underwriter uploads a submission (e.g., an email
    # with SOV attachment) to PingVision for processing. This kicks off the
    # automated intake and clearance workflow.
    # ==========================================================================
    print(color_text("\nStep 2: Creating submission...", "yellow"))

    pingid = create_submission(base_url, headers, team_uuid, eml_path)

    print(color_text(f"  Created submission: {pingid}", "green"))

    # ==========================================================================
    # Step 3: Start Background Event Polling
    # ==========================================================================
    # USER ACTION: Start polling for submission events to track status changes.
    # In production, this typically runs as a background process watching all
    # submissions for your team/division.
    # ==========================================================================
    print(color_text("\nStep 3: Starting background event polling...", "yellow"))

    earliest_allowed_time = datetime.now(timezone.utc)

    threading.Thread(
        target=poll_submission_events,
        args=(
            base_url,
            headers,
            division_uuid,
            team_uuid,
            pingid,
            earliest_allowed_time,
        ),
        name="event_poller",
        daemon=True,
    ).start()

    # ==========================================================================
    # Step 4: Wait for Pending Clearance, then Advance to Data Entry
    # ==========================================================================
    # PING: The clearance team reviews the submission for conflicts (e.g.,
    # incumbent carriers, duplicate submissions). If cleared, they advance
    # through "Cleared" to "Data Entry" where Ping's AI processing begins.
    # ==========================================================================
    print(color_text("\nStep 4: Waiting for Pending Clearance status...", "yellow"))

    wait_for_status(pingid, "Pending Clearance", status_uuids)

    print(color_text("\n  Advancing to Cleared...", "yellow"))
    change_status(base_url, headers, pingid, status_uuids["Cleared"])
    wait_for_status(pingid, "Cleared", status_uuids)

    print(color_text("\n  Advancing to Data Entry...", "yellow"))
    change_status(base_url, headers, pingid, status_uuids["Data Entry"])
    wait_for_status(pingid, "Data Entry", status_uuids)

    # ==========================================================================
    # Step 5: Ping Certifies Data
    # ==========================================================================
    # PING: Ping's AI and human-in-the-loop process downloads the scrubber,
    # reviews/corrects the extracted data, and certifies the submission.
    # This triggers the transition to Underwriting.
    #
    # For the sake of this demo script, we simplify this step:
    #   - Only do this in staging, not production
    #   - Uses Update Submission API with is_building_data_ready=True
    # ==========================================================================
    print(color_text("\nStep 5: Ping certifies data...", "yellow"))
    print(color_text("  (In production: Ping's team certifies via scrubber)", "red"))

    # [DEMO] Auto-advance to Underwriting and mark data as ready
    # In production, this is triggered by Ping's certification process
    print(color_text("  [DEMO] Auto-advancing to Underwriting...", "yellow"))
    change_status(base_url, headers, pingid, status_uuids["Underwriting"])

    # Mark building data as ready - this triggers the RUN_OUTPUTTERS job
    # In production, this flag is set when Ping's certification is complete
    print(color_text("  [DEMO] Marking building data as ready...", "yellow"))
    update_submission(base_url, headers, pingid, to_update="is_building_data_ready", value=True)

    # ==========================================================================
    # Step 6: Wait for Underwriting Status
    # ==========================================================================
    # USER ACTION: Poll submission events to watch for the transition to
    # "Underwriting" status after Ping completes certification.
    # ==========================================================================
    wait_for_status(pingid, "Underwriting", status_uuids)

    # ==========================================================================
    # Step 7: Wait for RUN_OUTPUTTERS Job to Complete
    # ==========================================================================
    # PING: Once building data is marked ready, Ping's backend triggers the
    # RUN_OUTPUTTERS job which generates final output files (JSON, Excel)
    # with all enriched and certified data.
    # ==========================================================================
    print(color_text("\nStep 7: Waiting for final outputs...", "yellow"))

    submission = wait_for_job(base_url, headers, pingid, team_uuid, division_uuid, "RUN_OUTPUTTERS")

    # ==========================================================================
    # Step 8: Download Output Documents
    # ==========================================================================
    # USER ACTION: Download the final JSON output containing all extracted,
    # enriched, and certified SOV data. This is typically consumed by
    # downstream systems (rating engines, policy admin, data warehouses).
    # ==========================================================================
    print(color_text("\nStep 8: Downloading output documents...", "yellow"))

    os.makedirs("workflow_example_results", exist_ok=True)

    for doc in submission.get("documents", []):
        doc_type = doc.get("document_type", "")
        filename = doc.get("filename", "")

        # Download only the JSON output (machine-readable structured data)
        if doc_type == "SOVFIXER_JSON" and not doc.get("is_archived", False):
            output_path = f"workflow_example_results/{pingid}_{filename}"
            download_document(base_url, headers, pingid, filename, output_path)
            print(color_text(f"  ✓ Saved {doc_type}: {output_path}", "green"))

    print(color_text(f"\n✓ Workflow complete for submission {pingid}", "green"))
    return pingid


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run PingVision clearance workflow using raw HTTP requests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python clear_and_triage_api.py --eml demo_email.eml --company "Ping Intel" --team "Ping Intel"
  python clear_and_triage_api.py --eml submission.eml --company "Acme" --team "Acme" --api-url "http://localhost:8002"
        """,
    )
    parser.add_argument("--eml", required=True, help="Path to .eml file to submit")
    parser.add_argument("--company", required=True, help="Company name in PingVision")
    parser.add_argument("--team", required=True, help="Team name in PingVision")
    parser.add_argument(
        "--api-url",
        default="http://localhost:8002",
        help="PingVision API base URL (default: localhost:8002)",
    )
    parser.add_argument(
        "--auth-token",
        default=None,
        help="API auth token (default: PINGVISION_AUTH_TOKEN_LOCAL env var)",
    )

    args = parser.parse_args()

    try:
        pingid = run_clearance_workflow(
            eml_path=args.eml,
            company_name=args.company,
            team_name=args.team,
            api_url=args.api_url,
            auth_token=args.auth_token,
        )
    except KeyboardInterrupt:
        print(color_text("\nWorkflow interrupted by user", "yellow"))
    except Exception as e:
        print(color_text(f"\nError: {e}", "red"))
        raise
