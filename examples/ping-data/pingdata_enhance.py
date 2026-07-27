#!/usr/bin/env python3

import pathlib
import site
from pprint import pprint

site.addsitedir("../src")

from pingintel_api import PingDataAPIClient

"""
Example script demonstrating how to use the Ping.Data API client for address enhancement,
including client initialization and basic enhancement requests.

Installation:
    pip install pingintel-api

Usage:
    Modify the address and parameters as needed and run the script.

Example output of a Lightbox Geocoded address:
    {'id': '170c479e-89e8-11f1-88b5-0242ac11000a',
     'location_data': {'LBG': {'address_id': '06072AHRRCTNDRUUKLJZWS',
                               'address_line_1': '42 Dolphin St',
                               'address_line_1_score': 1,
                               'address_line_2': None,
                               'assessment_id': '0306H4VEINZ8C9CU096JP9',
                               'city': 'Hitchcock',
                               'city_score': 1,
                               'confidence': 100,
                               'country': 'US',
                               'country_subdivision_code': 'TX',
                               'country_subdivision_name': 'Texas',
                               'county': 'Galveston',
                               'error_message': None,
                               'fetch_time': 0.206,
                               'formatted_address': '42 Dolphin St, Hitchcock, TX '
                                                    '77563-2581, US',
                               'is_success': True,
                               'latitude': 29.326512,
                               'location_type': 'ROOFTOP',
                               'longitude': -94.94596,
                               'parcel_id': '0205VTOPLMJMNT3BHYMCUR',
                               'postal_code': '77563',
                               'postal_code_score': 1,
                               'precision': 100,
                               'precision_code': 10,
                               'route': 'Dolphin St',
                               'route_score': 1,
                               'score': 1,
                               'state': 'TX',
                               'state_code': 'TX',
                               'state_name': 'Texas',
                               'status_code': 200,
                               'street_number': '42',
                               'street_number_score': 1,
                               'structure_id': '0505OD6SO1BUZ4EW9YBOPS'}}}
"""

SCRIPT_DIR = pathlib.Path(__file__).parent

api_client = PingDataAPIClient(environment="dev")

addresses = [
    "42 Galaxy St, Fort Liberty, NC 28307",
    "42 Adams Street, Quincy, MA",
    "42 Dolphin St, Hitchcock, TX 77563, USA",
    "Café at the End of the Universe 2800 E Observatory Rd, Los Angeles, CA 90027",
]
pprint(f"Don't Panic! Processing address enhancement for {addresses} . . . ")
print()

for address in addresses:
    try:
        # Make the API call to enhance the address
        result = api_client.enhance(
            address=address,
            sources=["LBG"],  # Using Lightbox Geocoding source as an example
            timeout=42,
            include_raw_response=False,
        )
        pprint(result)

        # Example of accessing specific fields
        if result.get("location_data", {}).get("LBG", {}).get("is_success"):
            location = result["location_data"]["LBG"]
            print(
                f"""Extracted location details:
               Latitude: {location['latitude']}
               Longitude: {location['longitude']}
               Formatted Address: {location['formatted_address']}
               Confidence: {location['confidence']}
               Precision: {location['precision']}"""
            )
            print()
    except Exception as e:
        pprint(f"Failed to enhance address - Time to consult the Guide: {str(e)}")
