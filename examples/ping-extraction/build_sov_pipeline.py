"""
Ping.Extraction SOV pipeline demo: submit parsing jobs, poll /sov/history
for revisions, fire one SOV update (SUD), download data-ready outputs.

Set SOVFIXER_AUTH_TOKEN, then run with `python build_sov_pipeline.py`.
"""

import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import requests


@dataclass(frozen=True)
class PingRevision:
    id: str
    revision: int
    record_type: str
    is_data_ready: bool = False


@dataclass
class PingSubmission:
    pingid: str
    revisions: set[PingRevision] = field(default_factory=set)

    def add_revision(
        self, record_type: str, revision: int, id: str, is_data_ready: bool
    ):
        self.revisions.add(
            PingRevision(
                record_type=record_type,
                revision=revision,
                id=id,
                is_data_ready=is_data_ready,
            )
        )


# Auth token. Generate one at https://auth.pingintel.com/account/api_keys/
API_KEY = os.environ.get("SOVFIXER_AUTH_TOKEN")
if not API_KEY:
    raise SystemExit("SOVFIXER_AUTH_TOKEN is not set")

BASE_URL = "https://api.sovfixer.com/api/v1"
HISTORICAL_SOVS_URL = f"{BASE_URL}/sov/history"
START_JOB_URL = f"{BASE_URL}/sov"

headers = {"Authorization": f"Token {API_KEY}"}

# File to upload when submitting parsing jobs.
SAMPLE_FILE = Path("parse_sov_testfile.xlsx")

# Corrections CSV uploaded when submitting the SOV update. Its rows must
# reference buildings present in SAMPLE_FILE (by item_key, or sheet_name plus
# sheet_row_number), since the update targets a SOV parsed from that file.
LOCATIONS_CSV = Path("corrections.csv")

# Where downloaded outputs land.
OUTPUT_DIR = Path("workflow_example_results")

POLL_SECONDS = 30


def submit_job() -> str:
    """Submit one SOV parsing job and return its ID."""
    payload = {
        "document_type": "SOV",
        "output_formats": ["json"],
        "integrations": ["PG"],
    }
    with SAMPLE_FILE.open("rb") as fh:
        files = {"file": (SAMPLE_FILE.name, fh)}
        response = requests.post(
            START_JOB_URL, data=payload, files=files, headers=headers
        )
    response.raise_for_status()
    job_id = response.json()["id"]
    print(f"Submitted parsing job: {job_id}")
    return job_id


def submit_sud(sovid: str) -> str:
    """Update a parsed SOV: open the job, upload locations, start processing.
    The resulting SUD revisions group under the parent sovid in the history feed."""
    # Open an update job tied to the parent SOV.
    resp = requests.post(f"{BASE_URL}/sov/{sovid}/initiate_update", headers=headers)
    resp.raise_for_status()
    update_id = resp.json()["id"]

    # Upload the revised building attributes.
    with LOCATIONS_CSV.open("rb") as fh:
        files = {"file": (LOCATIONS_CSV.name, fh)}
        resp = requests.post(
            f"{BASE_URL}/sov/update/{update_id}/add_locations",
            files=files,
            headers=headers,
        )
    resp.raise_for_status()

    # Start processing. extra_data is optional but drives the output filename.
    resp = requests.post(
        f"{BASE_URL}/sov/update/{update_id}/start",
        headers=headers,
        json={"extra_data": {"insured_name": "Acme Corp"}, "output_formats": ["json"]},
    )
    resp.raise_for_status()
    print(f"Submitted SOV update (SUD): {update_id}")
    return update_id


def check_sud_status(update_id: str) -> str:
    """Return the SUD's current status. A failed SUD only surfaces here, never
    in the history feed, so this is the only place a failure is detected."""
    response = requests.get(f"{BASE_URL}/sov/update/{update_id}", headers=headers)
    response.raise_for_status()
    data = response.json()
    status = data["request"]["status"]
    if status == "FAILED":
        result = data.get("result", {})
        print(
            f"  ! SUD {update_id} FAILED: "
            f"{result.get('status')}: {result.get('message')}"
        )
    elif status == "COMPLETE":
        print(f"  SUD {update_id} complete.")
    return status


def fetch_output(record_id: str) -> bool:
    """Download the latest output for a record. Return True when done with it.
    False means not ready yet, retry next poll. Output generation is async."""
    # `revision: -1` requests the most recent revision's output for this submission.
    payload = {"output_format": "json", "revision": -1, "overwrite_existing": False}
    print(f"  Fetching output for {record_id}...")
    response = requests.post(
        f"{BASE_URL}/sov/{record_id}/get_or_create_output",
        headers=headers,
        json=payload,
    )
    response.raise_for_status()
    data = response.json()

    status = data["request"]["status"]
    if status == "FAILED":
        print(f"  ! Output generation for {record_id} failed, giving up on it.")
        return True
    if status != "COMPLETE":
        print(
            f"  Output for {record_id} not ready yet (status={status}), "
            f"will retry next poll."
        )
        return False

    file_response = requests.get(data["result"]["url"], headers=headers)
    file_response.raise_for_status()
    output_path = OUTPUT_DIR / data["result"]["scrubbed_filename"]
    output_path.write_bytes(file_response.content)
    print(f"  Saved {output_path}")
    return True


# Used to recognize our own SOVs in the history feed.
submitted_job_ids: set = set()

# Capture the start time before submitting so the first poll catches every
# job in the batch.
start = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

# Submit an initial batch so the poll loop has activity to observe from the start.
OUTPUT_DIR.mkdir(exist_ok=True)
print("Submitting initial batch of jobs...")
for _ in range(3):
    submitted_job_ids.add(submit_job())

# Cursor is None on the first poll. Subsequent polls pass the value returned
# by the previous response to fetch only records added since.
last_cursor_id = None

# Group revisions by submission. A record's pingid links it to a Ping.Vision
# submission. Fall back to sovid for standalone records. The demo only prints
# from this. It models the state a real integration would keep and act on,
# e.g. to drive work from each submission's latest data-ready revision.
submissions: dict[str, PingSubmission] = {}

# Data-ready records whose outputs haven't been downloaded yet.
pending_downloads: set[str] = set()

# Fire exactly one SOV update, the first time one of our parsing jobs completes.
sud_submitted = False
sud_update_id = None

poll_count = 0

while True:
    poll_count += 1
    params = {"cursor_id": last_cursor_id, "start": start, "page_size": 10}
    response = requests.get(HISTORICAL_SOVS_URL, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()

    # Advance the cursor for the next poll. Keep the prior cursor if an empty
    # page omits or nulls cursor_id, so we resume after the last record we saw
    # rather than replaying from `start`.
    last_cursor_id = data.get("cursor_id") or last_cursor_id

    print(f"Poll #{poll_count}: fetched {len(data['results'])} record(s)")

    for record in data["results"]:
        submission_key = record["pingid"] or record["sovid"]
        if submission_key not in submissions:
            submissions[submission_key] = PingSubmission(pingid=submission_key)
            print(f"--- New submission: {submission_key} ---")

        submissions[submission_key].add_revision(
            record_type=record["record_type"],
            revision=record.get("revision"),
            id=record["id"],
            is_data_ready=bool(record.get("is_data_ready")),
        )

        kind = "SOV" if record["record_type"] == "ORIG" else "SUD"
        state = "complete" if record.get("status") == "C" else "failed"
        print(f"  + {kind} {record['record_type']} ({state}): {record['id']}")

        if record.get("status") == "F":
            print(f"  ! {record['id']} failed, skipping update and download")
            continue

        # Update the first completed ORIG SOV submitted
        if (
            not sud_submitted
            and record["record_type"] == "ORIG"
            and record["sovid"] in submitted_job_ids
        ):
            print(
                f"  First of our SOVs complete, submitting an update "
                f"for {record['sovid']}"
            )
            sud_update_id = submit_sud(record["sovid"])
            sud_submitted = True

        # The feed flags each record's data as ready to download via
        # is_data_ready. Queue ready records, revisit the rest next poll.
        if record.get("is_data_ready"):
            pending_downloads.add(record["id"])
        else:
            print(
                f"  Not data-ready yet, awaiting Ping HITL "
                f"certification: {record['id']}"
            )

    # Try queued downloads. Anything not ready stays queued for the next poll.
    for record_id in list(pending_downloads):
        if fetch_output(record_id):
            pending_downloads.discard(record_id)

    # Track our SUD to a terminal state. On completion, queue its own output
    # for download. A failed SUD only surfaces here, never in the feed.
    if sud_update_id:
        sud_status = check_sud_status(sud_update_id)
        if sud_status == "COMPLETE":
            pending_downloads.add(sud_update_id)
            sud_update_id = None
        elif sud_status == "FAILED":
            sud_update_id = None

    print(
        f"Tracking {len(submissions)} submission(s), "
        f"polling again in {POLL_SECONDS}s..."
    )
    time.sleep(POLL_SECONDS)
