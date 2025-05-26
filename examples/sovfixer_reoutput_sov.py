import csv
import site

site.addsitedir("../src")

from pingintel_api import SOVFixerAPIClient

api_client = SOVFixerAPIClient()
fix_sov_ret = api_client.fix_sov("test_sov.xlsx")
sovid = fix_sov_ret["id"]

policy_terms = {
    "layer_terms": [
        {"name": "5M", "limit": 5000000, "participation": 1.0},
        {"name": "10M xs 5M", "attachment": 5000000, "limit": 10000000, "participation": 0.75},
    ],
    "peril_terms": [
        {
            "group": "EQ",
            "subperil_types": ["EQ_Shake", "EQ_Sprinkler", "EQ_Landslide", "EQ_Tsunami", "EQ_Liquefaction"],
            "sublimit": 3000000,
        },
        {
            "group": "EQ2",
            "subperil_types": ["EQ_Fire"],
            "sublimit": 2000000,
            "location_deductible_type": "C",
            "location_deductible": 0.05,
        },
        {
            "group": "HU",
            "subperil_types": ["HU_Wind", "HU_PrecipitationFlood"],
            "min_deductible": 100000,
            "max_deductible": 150000,
        },
        {
            "group": "SCS",
            "subperil_types": ["Hail", "StraightLineWind", "Tornado", "WinterStorm"],
            "bi_days_deductible": 10,
        },
        {
            "group": "IF",
            "subperil_types": ["InlandFlood"],
        },
        {
            "group": "WF",
            "subperil_types": ["Wildfire"],
        },
        {
            "group": "TE",
            "subperil_types": ["Terrorism"],
        }
    ],
    "zone_terms": [
        {
            "peril_class": "HU",
            "zone": "AllOther",
            "is+excluded": True,
        },
        {
            "peril_class": "SCS",
            "zone": "AllOther",
            "is_excluded": False,
            "location_deductible_type": "S",
            "location_deductible": 0.03,
        },
        {
            "peril_class": "IF",
            "zone": "SFHA",
            "sublimit": 4000000,
            "min_deductible": 100000,
            "max_deductible": 500000,
            "is_excluded": False,
            "location_deductible_type": "S",
        },
    ],
    "excluded_subperil_types": ["HU_Surge"],
}

extra_data={
    "insured_name": "My Test",
}

metadata = {
    "Timestamp": 1748261077,
    "Name": "My Filename.xlsm",
    "UserInfo": {
        "UserName": "Jane Doe",
    }
}

update_sov_ret = api_client.update_sov(
    sovid,
    location_filenames=["test_reoutput_locations.csv"],
    extra_data=extra_data,
    policy_terms=policy_terms,
    policy_terms_format_name="PINGv2",
    actually_write=True,
    output_formats=["JSON", "AMRISC"],
    metadata=metadata,
)
print(update_sov_ret)
