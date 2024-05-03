import site
from pprint import pprint

site.addsitedir("../src")

from pingintel_api import PingVisionAPIClient

api_client = PingVisionAPIClient(environment="dev2")  # api_url="http://127.0.0.1:8002")
activity_results = api_client.list_submission_activity(page_size=5)

pprint(activity_results)
# for activity in activity_results["results"]:
#     pprint(activity)
