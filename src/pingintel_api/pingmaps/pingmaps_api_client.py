#!/usr/bin/env python

# Copyright 2021-2024 Ping Data Intelligence

import logging
import os
import pprint
import time
from timeit import default_timer as timer
from typing import IO, NotRequired, TypedDict, overload, Unpack

import click
import requests

from pingintel_api.api_client_base import APIClientBase

from .. import constants as c
from ..utils import is_fileobj, log, raise_for_status
from . import types as t

logger = logging.getLogger(__name__)


class PingMapsAPIClient(APIClientBase):
    api_subdomain = "app"
    api_base_domain = "pingintel.com"
    auth_token_env_name = "SOVFIXER_AUTH_TOKEN"
    product = "pingmaps"

    def get_policy_locations(
        self, **kwargs: Unpack[t.PingMapsPolicyLocationRequest]
    ) -> t.PingMapsPolicyLocationResponse:
        url = self.api_url + "/api/v1/pli/policy"

        response = self.get(url, params=kwargs)

        raise_for_status(response)
        response_data = response.json()
        return response_data

    def get_policy_breakdown(self, **kwargs: Unpack[t.PingMapsPolicyBreakdownRequest]):
        url = self.api_url + "/api/v1/pli/policy_breakdown"
        response = self.get(url, params=kwargs)
        raise_for_status(response)
        response_data = response.json()
        return response_data
