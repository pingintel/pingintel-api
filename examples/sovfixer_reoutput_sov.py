import csv
import site

site.addsitedir("../src")

from pingintel_api import SOVFixerAPIClient

api_client = SOVFixerAPIClient()
sovid = api_client.fix_sov("test_sov.xlsx")

policy_terms = {
    "layer_terms": [
      {
        "name": "5M",
        "limit": 5000000,
        "participation": 1.0
      },
      {
        "name": "10M xs 5M",
        "attachment": 5000000,
        "limit": 10000000,
        "participation": 0.75
      }
    ],
    "peril_terms": {
      "EQ": {
        "subperil_types": [
          "EQ_Shake",
          "EQ_Sprinkler",
          "EQ_Landslide",
          "EQ_Tsunami",
          "EQ_Liquefaction"
        ],
        "sublimit": 3000000,
      },
      "EQ2": {
        "subperil_types": [
          "EQ_Fire"
        ],
        "sublimit": 2000000,
        "location_deductible_type": "C",
        "location_deductible": 0.05
      },
      "HU": {
        "subperil_types": [
          "HU_Wind",
          "HU_PrecipitationFlood"
        ],
        "min_deductible": 100000,
        "max_deductible": 150000,
      },
      "SCS": {
        "subperil_types": [
          "Hail",
          "StraightLineWind",
          "Tornado",
          "WinterStorm"
        ],
        "bi_days_deductible": 10,
      },
      "IF": {
        "subperil_types": [
          "InlandFlood"
        ],
      },
      "WF": {
        "subperil_types": [
          "Wildfire"
        ],
      },
      "TE": {
        "subperil_types": [
          "Terrorism"
        ],
      }
    },
    "zone_terms": {
      "HU": {
        "AllOther": {
          "is_excluded": True,
        }
      },
      "SCS": {
        "AllOther": {
          "is_excluded": False,
          "location_deductible_type": "S",
          "location_deductible": 0.03
        }
      },
      "IF": {
        "SFHA": {
          "sublimit": 4000000,
          "min_deductible": 100000,
          "max_deductible": 500000,
          "is_excluded": False,
          "location_deductible_type": "S",
        }
      }
    },
    "excluded_subperil_types": [
      "HU_Surge"
    ]
  }

api_client.reoutput_sov(
    sovid, 
    location_filenames=["test_reoutput_locations.csv"], 
    extra_data={"insured_name": "My Test",}, 
    policy_terms=policy_terms, 
    policy_terms_format_name="PINGv2", 
    actually_write=True, 
    output_formats=["JSON", "AMRISC"],
)
