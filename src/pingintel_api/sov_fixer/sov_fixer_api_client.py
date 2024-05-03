#!/usr/bin/env python

# Copyright 2021-2024 Ping Data Intelligence

import logging
import os
import pprint
import time
from typing import IO, NotRequired, TypedDict, overload

import click
import requests

from pingintel_api.api_client_base import APIClientBase

from .. import constants as c
from ..utils import is_fileobj, log, raise_for_status
from . import types as t

logger = logging.getLogger(__name__)


class SOVFixerAPIClient(APIClientBase):
    api_subdomain = "api"
    api_base_domain = "sovfixer.com"
    auth_token_env_name = "SOVFIXER_AUTH_TOKEN"
    product = "sovfixer"

    SOV_STATUS = t.SOV_STATUS
    SOV_RESULT_STATUS = t.SOV_RESULT_STATUS

    def fix_sov_async_start(
        self,
        file: IO[bytes] | str,
        document_type,
        filename=None,
        callback_url=None,
        output_formats=None,
        client_ref=None,
        integrations=None,
        delegate_to: str | None = None,
    ):
        url = self.api_url + "/api/v1/sov"

        if is_fileobj(file):
            if filename is None:
                raise ValueError("Need filename if file is a file object.")

            files = {"file": (filename, file)}
        else:
            if not os.path.exists(file):
                raise click.ClickException(f"Path {file} does not exist.")

            files = {"file": open(file, "rb")}

        data = {}
        if callback_url:
            data["callback_url"] = callback_url
        if document_type:
            data["document_type"] = document_type
        if output_formats:
            data["output_formats"] = output_formats
        if client_ref:
            data["client_ref"] = client_ref
        if integrations is not None:
            data["integrations"] = integrations
        if delegate_to is not None:
            data["delegate_to"] = delegate_to

        response = self.session.post(url, files=files, data=data)
        if response.status_code == 200:
            pprint.pprint(response.json())
        else:
            pprint.pprint(response.text)

        raise_for_status(response)

        response_data = response.json()
        sov_id = response_data["id"]
        message = response_data["message"]
        status_url = self.api_url + f"/api/v1/sov/{sov_id}"
        log(
            f"+ Dispatched {sov_id}: {message}.  Now, polling for results at {status_url}."
        )
        return response_data

    def fix_sov_async_check_progress(self, sovid_or_start_ret) -> t.FixSOVResponse:
        if isinstance(sovid_or_start_ret, dict):
            sov_id = sovid_or_start_ret["id"]
        else:
            sov_id = sovid_or_start_ret

        status_url = self.api_url + f"/api/v1/sov/{sov_id}?include_progress=true"
        # params = {"id": sov_id}

        response = self.session.get(status_url)
        # pprint.pprint(response.json())
        raise_for_status(response)

        response_data: t.FixSOVResponse = response.json()
        # request_status = response_data["request"]["status"]
        return response_data

    def fix_sov_download(self, output_ret, actually_write=False, output_path=None):
        output_url = output_ret["url"]
        if (
            self.environment
            and self.environment == "local2"
            and "api-local.sovfixer.com" in output_url
        ):
            output_url = output_url.replace("api-local.sovfixer.com", "localhost:8000")

        output_description = output_ret["description"]
        output_filename = output_ret["filename"]
        if output_path is None:
            output_path = output_filename

        log(f"Requesting output from {output_url}...")
        with self.session.get(output_url, stream=True) as response:
            raise_for_status(response)
            filesize_mb = int(response.headers.get("content-length", 0)) / 1024 / 1024
            pprint.pprint(dict(response.headers))
            log(f"  - Streaming {output_description} output ({filesize_mb:.2f} MB)...")

            if actually_write:
                with open(output_path, "wb") as fd:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        fd.write(chunk)
            log(f"  - Downloaded {output_description} output: {output_path}.")
        return output_path if actually_write else None

    def fix_sov(
        self,
        filename,
        *,
        document_type: str = "SOV",
        callback_url=None,
        actually_write=False,
        output_formats=None,
        client_ref=None,
    ):
        sov_fixer_client = self
        start_response = sov_fixer_client.fix_sov_async_start(
            filename,
            document_type=document_type,
            callback_url=callback_url,
            output_formats=output_formats,
            client_ref=client_ref,
        )

        while 1:
            response_data = sov_fixer_client.fix_sov_async_check_progress(
                start_response
            )
            # raise_for_status(response_data)
            # pprint.pprint(response_data)

            request_status = response_data["request"]["status"]
            pct_complete = response_data["request"]["pct_complete"]
            last_status = response_data["request"]["last_health_status"]

            POLL_SECS = 2.5
            if request_status == "PENDING":
                log("  - Has not yet been queued for processing.")
                time.sleep(POLL_SECS)
            elif request_status == "IN_PROGRESS":
                log(f"  - Still in progress ({pct_complete}% complete): {last_status}")
                time.sleep(POLL_SECS)
            else:
                break

        result_status = response_data["result"]["status"]
        result_message = response_data["result"]["message"]
        log(f"+ Finished with result {result_status}: {result_message}")

        if result_status == "SUCCESS":
            log("Complete!  Fetching outputs.")
            for output in response_data["result"]["outputs"]:
                output_url = output["url"]
                if (
                    self.environment
                    and self.environment == "local2"
                    and "api-local.sovfixer.com" in output_url
                ):
                    output_url = output_url.replace(
                        "api-local.sovfixer.com", "localhost:8000"
                    )

                output_filename = output["filename"]

                output_path = output_filename

                if actually_write:
                    if os.path.exists(output_path):
                        yesno = input(
                            f"Do you want to overwrite the existing file {output_path} [y/N]? "
                        )
                        if yesno.lower() != "y":
                            continue

                sov_fixer_client.fix_sov_download(
                    output,
                    actually_write=actually_write,
                    output_path=output_path,
                )
            return True
        else:
            log("* Parsing failed!  Raw API output:")
            log(response_data)
            return False

    def list_activity(
        self,
        cursor_id=None,
        prev_cursor_id=None,
        page_size=50,
        fields=None,
        search=None,
        origin=None,
        status=None,
        organization__short_name=None,
    ) -> t.ActivityResponse:
        parameters = {}
        if cursor_id:
            parameters["cursor_id"] = cursor_id
        elif prev_cursor_id:
            parameters["prev_cursor_id"] = prev_cursor_id
        if page_size:
            parameters["page_size"] = page_size
        if fields:
            parameters["fields"] = fields
        if search:
            parameters["search"] = search
        if origin:
            parameters["origin"] = origin
        if status:
            parameters["status"] = status
        if organization__short_name:
            parameters["organization__short_name"] = organization__short_name

        url = self.api_url + "/api/v1/sov/activity"
        response = self.session.get(url, params=parameters)
        raise_for_status(response)
        return response.json()
