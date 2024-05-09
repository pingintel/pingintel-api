import pathlib
import site
from pprint import pprint

site.addsitedir("../src")

from pingintel_api import PingVisionAPIClient

SCRIPT_DIR = pathlib.Path(__file__).parent

api_client = PingVisionAPIClient(environment="local", api_url="http://127.0.0.1:8002")
# api_client = PingVisionAPIClient(environment="dev2")  # api_url="http://127.0.0.1:8002")

ret = api_client.create_submission(
    files={"files": ("test_sov.xlsx", open(SCRIPT_DIR / "test_sov.xlsx", "rb"))}
)
print(f"pingid: {ret['id']}")
activity_results = api_client.list_submission_activity(page_size=5)

pprint(activity_results)
# for activity in activity_results["results"]:
#     pprint(activity)
