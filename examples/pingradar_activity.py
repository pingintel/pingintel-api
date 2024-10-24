import pathlib
import site
from pprint import pprint

site.addsitedir("../src")

from pingintel_api import PingRadarAPIClient

SCRIPT_DIR = pathlib.Path(__file__).parent

api_client = PingRadarAPIClient(environment="dev")

ret = api_client.create_submission(filepaths=[SCRIPT_DIR / "test_sov.xlsx"])
print(f"pingid: {ret['id']}")
activity_results = api_client.list_submission_activity(page_size=5)

pprint(activity_results)
# for activity in activity_results["results"]:
#     pprint(activity)
