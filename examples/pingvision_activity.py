import pathlib
import site
from pprint import pprint

site.addsitedir("../src")

from pingintel_api import PingVisionAPIClient

SCRIPT_DIR = pathlib.Path(__file__).parent
print(SCRIPT_DIR)

api_client = PingVisionAPIClient(environment="local")

TEST_DATA_SOV_DIR = "/Users/josephmisiti/mathandpencil/projects/boxandwhisker/boxandwhisker-sov-scrubber/testdata/SOV"

SOVS = [
    "8696955-2019.Statement.of.Values_ProspectPlace_123119-20_1.XLSX",
    "AAA Test SOV.XLSX",
    "Delaney at Parkway SOV (8-9-18).xls",
    "Marketing xls.xlsx",
    "mario (1).xlsx",
    "Scot Holding Assurant Flood Chart-VOYAGER-WB.xlsx"
]

for sov in SOVS:
    ret = api_client.create_submission(
        files={"files": (sov, open(TEST_DATA_SOV_DIR + "/" + sov, "rb"))}
    )



print(f"pingid: {ret['id']}")
activity_results = api_client.list_submission_activity(page_size=5)

pprint(activity_results)
# for activity in activity_results["results"]:
#     pprint(activity)
