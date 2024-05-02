#!/usr/bin/env python

# Copyright 2021-2024 Ping Data Intelligence

import logging
import os
import pprint
import time
from timeit import default_timer as timer
from typing import overload, IO, TypedDict, NotRequired
import click
import requests

from pingintel_api.api_client_base import APIClientBase
from .. import constants as c
from . import types as t
from ..utils import is_fileobj, raise_for_status, log

logger = logging.getLogger(__name__)


class PingVisionAPIClient(APIClientBase):
    api_subdomain = "api"
    base_domain = "vision.pingintel.com"
    auth_token_env_name = "PINGVISION_AUTH_TOKEN"
    product = "pingvision"

    def _create_session(self):
        session = requests.Session()

        session.headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Accept-Encoding": "gzip",
        }
        breakpoint()

        return session

    def list_activity(
        self,
        cursor_id: str | None = None,
        prev_cursor_id: str | None = None,
        page_size: int | None = None,
        fields: list[str] | None = None,
        search: str | None = None,
        organization__short_name: str | None = None,
    ) -> t.PingVisionListActivityResponse:
        url = self.api_url + "/api/v1/activity"

        data = {}
        if cursor_id:
            data["cursor_id"] = cursor_id
        if prev_cursor_id:
            data["prev_cursor_id"] = prev_cursor_id
        if page_size:
            data["page_size"] = page_size
        if fields:
            data["fields"] = fields
        if search:
            data["search"] = search
        if organization__short_name:
            data["organization__short_name"] = organization__short_name

        response = self.get(url, data=data)

        if response.status_code == 200:
            pprint.pprint(response.json())
        else:
            pprint.pprint(response.text)

        raise_for_status(response)

        response_data = response.json()
        return response_data
