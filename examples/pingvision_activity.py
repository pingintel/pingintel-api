import site

site.addsitedir("../src")

from pingintel_api import PingVisionAPIClient

api_client = PingVisionAPIClient(environment="dev")
api_client.list_activity("test_sov.xlsx")
