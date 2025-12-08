import site
import time

site.addsitedir("../src")

""" This example script will page through all activity, starting from the most recent. """

from pingintel_api import SOVFixerAPIClient

api_client = SOVFixerAPIClient(environment="prod2")

next_cursor_id = None
total_count = None
cnt = 0
while True:
    response = api_client.list_activity(
        cursor_id=next_cursor_id,
        fields=["filename", "status", "id", "revision"],
    )
    next_cursor_id = response.get("cursor_id")
    remaining_count = response.get("remaining_count")
    if total_count is None:
        total_count = remaining_count + len(response["results"])
    if len(response["results"]) == 0:
        break
    for activity in response["results"]:
        cnt += 1

        print(
            f"{cnt}/{total_count}: {activity['filename']}: {activity['status']} {activity['id']} rev{activity['revision']}"
        )

    # time.sleep(0.25)
