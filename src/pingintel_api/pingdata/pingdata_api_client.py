#!/usr/bin/env python

# Copyright 2021-2024 Ping Data Intelligence

import logging
import os
import pprint
import time
from typing import Unpack

from pingintel_api.api_client_base import APIClientBase
from pingintel_api.pingdata import types as t

from ..utils import raise_for_status

logger = logging.getLogger(__name__)


class PingDataAPIClient(APIClientBase):
    api_subdomain = "api"
    api_base_domain = "pingintel.com"
    auth_token_env_name = "PING_DATA_AUTH_TOKEN"
    product = "pingdata"
    include_legacy_dashes = True

    def enhance(
        self,
        *,
        sources: list[str],
        timeout: float | None = None,
        include_raw_response: bool = False,
        nocache: bool = False,
        **extra_location_kwargs: Unpack[t.Location],
    ):
        """
        Enhance one or more locations with additional geocoding data.

        :param address: List of addresses to enhance. Each address should be a string. Multiple addresses can be passed.
                       Example:["42 Galaxy St, Fort Liberty, NC 28307", "42 Adams Street, Quincy, MA"]
        :type address: list[str]

        :param sources: List of geocoding sources to use. Multiple sources can be passed.
                       Example: ["GG"] for Google Geocoding
        :type sources: list[str]

        :param country: Optional ISO2A country code to provide a hint to the geocoder.
        :type country: str|None

        :param timeout: Maximum time to wait for response in seconds.
                       If None, uses default timeout.
        :type timeout: float|None

        :param include_raw_response: If True, includes the complete raw response from
                                    geocoding services in the result.
        :type include_raw_response: bool

        :return: Dictionary containing enhanced location data for each address,
                including coordinates, formatted addresses, and confidence scores.
        :rtype: dict

        :raises: RequestException: If the API request fails
                ValueError: If invalid addresses or sources are provided
        """

        if not extra_location_kwargs:
            extra_location_kwargs = {}

        data = {**extra_location_kwargs}

        url = self.api_url + "/api/v1/enhance"

        if timeout is not None:
            data["timeout"] = float(timeout)

        data["sources"] = sources
        data["include_raw_response"] = include_raw_response

        if nocache:
            data["check_cache"] = False

        response = self.get(url, params=data)

        raise_for_status(response)
        response_data = response.json()
        return response_data

    def bulk_enhance(
        self,
        *,
        locations: list[t.Location],
        sources: list[str],
        timeout: float | None = None,
        include_raw_response: bool = False,
        nocache: bool = False,
        callback_url: str | None = None,
        poll_seconds: float = 5.0,
        fetch_outputs: bool = False,
        verbose: int = 1,
    ):
        """
        Enhance one or more locations with additional geocoding data.

        :param locations: List of locations to enhance.

        :param sources: Default geocoding sources to use. Multiple sources can be passed.
                        Can be overridden for each location.
                       Example: ["GG"] for Google Geocoding
        :type sources: list[str]

        :param timeout: Maximum time to wait for response in seconds.
                       If None, uses default timeout.
        :type timeout: float|None

        :param include_raw_response: If True, includes the complete raw response from
                                    geocoding services in the result.
        :type include_raw_response: bool

        :return: GUID of the bulk job
        :rtype: str

        :raises: RequestException: If the API request fails
                ValueError: If invalid addresses or sources are provided
        """

        start_time = time.time()
        response_data = self.bulk_enhance_async_start(
            location_data=locations,
            sources=sources,
            callback_url=callback_url,
            timeout=timeout,
            include_raw_response=include_raw_response,
            nocache=nocache,
        )
        request_id = response_data["id"]
        message = response_data["message"]

        self.logger.info(
            f"+ Dispatched {request_id}: {message}.  Now, polling for results at {self.bulk_enhance_async_get_status_url(request_id=request_id)}."
        )

        while 1:
            response_data = self.bulk_enhance_async_check_progress(request_id=request_id)
            # if not quiet:
            #     pprint.pprint(response_data)
            request_status = response_data["request"]["status"]

            if request_status == "PENDING":
                self.logger.info(f"  - Has not yet been queued for processing, checking progress in {poll_seconds}s.")
                time.sleep(poll_seconds)
            elif request_status == "QUEUED":
                self.logger.info(f"  - Queued, checking progress in {poll_seconds}s.")
                time.sleep(poll_seconds)
            elif request_status == "IN_PROGRESS":
                self.logger.info(f"  - Still in progress, checking progress in {poll_seconds}s.")
                time.sleep(poll_seconds)
            else:
                break

        try:
            result_status = response_data["result"]["status"]
            result_message = response_data["result"]["message"]
        except:
            raise

        self.logger.info(
            f"Finished {len(locations)} items with result {result_status}: {result_message}: {time.time()-start_time:.1f}s."
        )

        if result_status == "SUCCESS":
            if fetch_outputs:
                actually_write = True
                self.logger.info("Complete!  Fetching outputs.")
                for output in response_data["result"]["outputs"]:
                    output_url = output["url"]
                    output_filename = output["filename"]
                    output_description = output["description"]

                    output_path = output_filename

                    if actually_write:
                        if os.path.exists(output_path):
                            yesno = input(f"Do you want to overwrite the existing file {output_path} [y/N]? ")
                            if yesno.lower() != "y":
                                continue

                    self.logger.info(f"Requesting output from {output_url}...")
                    response = self.get(output_url)
                    raise_for_status(response)
                    if actually_write:
                        with open(output_path, "wb") as fd:
                            for chunk in response.iter_content(chunk_size=128):
                                fd.write(chunk)
                    if output:
                        pprint.pprint(response.json())
                    self.logger.info(f"  - Downloaded {output_description} output: {output_path}.")
            return True
        else:
            self.logger.warning(f"* Parsing failed!  Raw API output:\n{response_data}")
            return False

    def bulk_enhance_async_start(
        self, location_data, sources, callback_url=None, timeout=None, include_raw_response=False, nocache=None
    ):
        data = {"locations": location_data}
        if callback_url:
            data["callback_url"] = callback_url
        if timeout is not None:
            data["timeout"] = timeout
        data["sources"] = sources

        data["include_raw_response"] = include_raw_response
        check_cache = not nocache
        data["check_cache"] = check_cache

        # if not self.quiet:
        #     pprint.pprint(data)
        response = self.post(self.api_url + "/api/v1/bulk_enhance", json=data, timeout=None)
        raise_for_status(response)

        response_data = response.json()
        return response_data

    def bulk_enhance_async_get_status_url(self, request_id):
        status_url = self.api_url + f"/api/v1/bulk_enhance/{request_id}"
        return status_url

    def bulk_enhance_async_check_progress(self, request_id):
        while True:
            response = self.get(self.bulk_enhance_async_get_status_url(request_id=request_id))
            if response.ok:
                break
            else:
                self.logger.warning(f"retrying get-progress: {response.status_code}: {response.text}")
                time.sleep(0.25)
        raise_for_status(response)
        response_data = response.json()
        return response_data
