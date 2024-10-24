#!/usr/bin/env python

# Copyright 2021-2024 Ping Data Intelligence

import logging

from pingintel_api.api_client_base import APIClientBase

from ..utils import raise_for_status

logger = logging.getLogger(__name__)


class PingDataAPIClient(APIClientBase):
    api_subdomain = "api"
    api_base_domain = "pingintel.com"
    auth_token_env_name = "PING_DATA_AUTH_TOKEN"
    product = "pingdata"
    include_legacy_dashes = True

    def enhance_data(
        self,
        address: list[str],
        sources: list[str],
        timeout: float | None = None,
        include_raw_response: bool = False,
        extra_location_kwargs: dict | None = None,
    ):
        """
        Enhance one or more locations with additional geocoding data.

        :param address: List of addresses to enhance. Each address should be a string. Multiple addresses can be passed.
                       Example:["42 Galaxy St, Fort Liberty, NC 28307", "42 Adams Street, Quincy, MA"]
        :type address: list[str]

        :param sources: List of geocoding sources to use. Multiple sources can be passed.
                       Example: ["GG"] for Google Geocoding
        :type sources: list[str]

        :param timeout: Maximum time to wait for response in seconds.
                       If None, uses default timeout.
        :type timeout: float|None

        :param include_raw_response: If True, includes the complete raw response from
                                    geocoding services in the result.
        :type include_raw_response: bool

        :param extra_location_kwargs: Optional dictionary of additional parameters for
                                    location processing.
        :type extra_location_kwargs: dict|None

        :return: Dictionary containing enhanced location data for each address,
                including coordinates, formatted addresses, and confidence scores.
        :rtype: dict

        :raises: RequestException: If the API request fails
                ValueError: If invalid addresses or sources are provided
        """

        if not extra_location_kwargs:
            extra_location_kwargs = {}

        data = {"address": address, **extra_location_kwargs}

        url = self.api_url + "/api/v1/enhance"

        if timeout is not None:
            data["timeout"] = float(timeout)

        data["sources"] = sources
        data["include_raw_response"] = include_raw_response

        response = self.get(url, params=data)

        raise_for_status(response)
        response_data = response.json()
        return response_data
