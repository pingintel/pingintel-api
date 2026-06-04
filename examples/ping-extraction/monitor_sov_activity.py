import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pprint import pprint

import requests


@dataclass(frozen=True)
class HistoryItem:
    id: str
    revision: int
    record_type: str
    is_data_ready: bool = False


# Auth token; generate one at https://auth.pingintel.com/account/api_keys/
API_KEY = os.environ.get("SOVFIXER_AUTH_TOKEN")
BASE_URL = "https://api.sovfixer.com/api/v1"
HISTORICAL_SOVS_URL = f"{BASE_URL}/sov/history"

headers = {"Authorization": f"Token {API_KEY}"}

# `start` isn't required. leaving it out/passing null starts at the beginning of time.
start = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y%m%d%H%M%S")

# `cursor` is None on the first poll; subsequent polls pass the value returned
# by the previous response to fetch only records added since.
last_cursor_id = None

# Track revisions already reported, keyed by id, so overlapping pages don't print duplicates.
ids_seen: dict[str, HistoryItem] = {}


def process_record(record):
    """Perform storage, actions, logging, etc. here."""
    # `record_type` "ORIG" is an original SOV. Any other value indicates a later revision (SUD).
    kind = "SOV" if record["record_type"] == "ORIG" else "SUD"
    print(f"--- New {kind} ---")
    pprint(record)

    # Fetch full details for failed records to surface the error_message.
    if record["status"] == "F":
        details = requests.get(
            f"{HISTORICAL_SOVS_URL}/{record['id']}", headers=headers
        )
        details.raise_for_status()
        print("details:")
        pprint(details.json())


while True:
    params = {"cursor_id": last_cursor_id, "start": start, "page_size": 50}
    response = requests.get(HISTORICAL_SOVS_URL, headers=headers, params=params)
    response.raise_for_status()

    data = response.json()
    # Advance the cursor for the next poll.
    last_cursor_id = data["cursor_id"]

    for record in data["results"]:
        if record["id"] in ids_seen:
            continue
        ids_seen[record["id"]] = HistoryItem(
            id=record["id"],
            revision=record["revision"],
            record_type=record["record_type"],
            is_data_ready=record["is_data_ready"],
        )
        process_record(record)

    print("Waiting 30 seconds to poll again...")
    time.sleep(30)
