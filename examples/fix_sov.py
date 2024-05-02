import site

site.addsitedir("../src")

from pingintel_api import SOVFixerAPIClient

api_client = SOVFixerAPIClient()
api_client.fix_sov("test_sov.xlsx")
