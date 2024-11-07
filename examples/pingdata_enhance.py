#!/usr/bin/env python3

import pathlib
import site
from pprint import pprint

site.addsitedir("../src")

from pingintel_api import PingDataAPIClient

"""
Example script demonstrating how to use the PingIntel Data API client for address enhancement, 
including client initialization and basic enhancement requests.

Installation:
    pip install pingintel-api

Usage:
    Modify the address and parameters as needed and run the script.

Example output of a Google Geocoded address:
    {'id': '77b078a8-9215-11ef-9774-0242ac110010',
     'location_data': {'GG': {'address_line_1': '42 Dolphin St',
                              'address_line_2': None,
                              'city': 'Hitchcock',
                              'confidence': 80,
                              'country': 'US',
                              'county': 'Galveston',
                              'error_message': None,
                              'fetch_time': 0.015,
                              'formatted_address': '42 Dolphin St, Hitchcock, TX '
                                                   '77563, USA',
                              'is_cache_hit': True,
                              'is_success': True,
                              'latitude': 29.326504,
                              'location_type': 'ROOFTOP',
                              'longitude': -94.945988,
                              'place_id': 'ChIJP7ee_XeCP4YR31uHe9aGi5s',
                              'postal_code': '77563',
                              'precision': 100,
                              'route': 'Dolphin St',
                              'state': 'TX',
                              'status_code': 200,
                              'street_number': '42'}}}
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
            address=[address],
            sources=["GG"],  # Using Google Geocoding source as an example
            timeout=42,
            include_raw_response=False,
        )
        pprint(result)

        # Example of accessing specific fields
        if result.get("location_data", {}).get("GG", {}).get("is_success"):
            location = result["location_data"]["GG"]
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
