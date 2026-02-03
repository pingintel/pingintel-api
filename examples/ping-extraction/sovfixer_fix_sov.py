import site

site.addsitedir("../src")

from pingintel_api import SOVFixerAPIClient

api_client = SOVFixerAPIClient(environment="prod", auth_token="xxx")
api_client.fix_sov("test_sov.xlsx")
# print(api_client.fix_sov_async_check_progress("s-ha-aon-95qfpq"))
