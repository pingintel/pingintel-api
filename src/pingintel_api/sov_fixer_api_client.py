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
from requests.exceptions import HTTPError
from . import constants as c

logger = logging.getLogger(__name__)


global start_time
start_time = None


def log(msg):
    global start_time
    if start_time is None:
        start_time = timer()
    elapsed = timer() - start_time
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    click.echo(f"[{timestamp} T+{elapsed:.1f}s] {msg}")


def raise_for_status(response: requests.Response):
    if response.ok:
        return

    error_msg = response.text
    log(f"{response.status_code} {response.reason}: {error_msg}")

    raise HTTPError(error_msg, response=response)


def is_fileobj(source):
    return hasattr(source, "read")


class FixSOVResponseRequest(TypedDict):
    status: c.SOV_STATUS
    requested_at: str
    progress_started_at: str
    completed_at: str | None
    last_health_check_time: str
    last_health_status: str
    pct_complete: int


class FixSOVResponseResultOutput(TypedDict):
    url: str
    description: str
    filename: str


class FixSOVResponseResult(TypedDict):
    message: str
    status: c.SOV_RESULT_STATUS
    outputs: list[FixSOVResponseResultOutput]


class FixSOVResponse(TypedDict):
    request: FixSOVResponseRequest
    result: NotRequired[FixSOVResponseResult]


class SOVFixerAPIClient:
    SOV_STATUS = c.SOV_STATUS
    SOV_RESULT_STATUS = c.SOV_RESULT_STATUS

    @overload
    def __init__(self, api_url: str, auth_token=None) -> None: ...

    @overload
    def __init__(self, environment: str = "prod", auth_token=None) -> None: ...

    def __init__(
        self,
        api_url: str | None = None,
        environment: str | None = "prod",
        auth_token=None,
    ):
        if api_url is None:
            assert environment, "Need either api_url or environment."
            if environment == "prod":
                api_url = "https://api.sovfixer.com"
            elif environment == "prod2":
                api_url = "https://api2.sovfixer.com"
            elif environment == "prodeu":
                api_url = "https://api.eu.sovfixer.com"
            elif environment == "local":
                api_url = "http://api-local.sovfixer.com"
            elif environment == "local2":
                api_url = "http://localhost:8000"
            else:
                api_url = f"https://api-{environment}.sovfixer.com"

        if auth_token is None:
            if environment in ["staging", "staging2"]:
                serverspace = "stg"
            elif environment in ["prod", "prod2"]:
                serverspace = "prd"
            elif environment in ["prodeu", "prodeu2"]:
                serverspace = "prdeu"
            elif environment in ["dev", "dev2"]:
                serverspace = "dev"
            elif environment in ["local", "local2"]:
                serverspace = "local"
            else:
                raise ValueError("Unknown environment and missing auth_token.")
            auth_token = os.environ.get(f"PING_{serverspace}_AUTH_TOKEN".upper())

        if auth_token is None:
            auth_token = os.environ.get("SOVFIXER_AUTH_TOKEN")
        if auth_token is None:
            raise ValueError(
                "Need --auth-token or SOVFIXER_AUTH_TOKEN environment variable set."
            )
        assert api_url
        self.api_url = api_url
        self.auth_token = auth_token
        self.session = requests.Session()
        self.session.headers = {
            "Authorization": f"Token {self.auth_token}",
            "Accept-Encoding": "gzip",
        }
        self.environment = environment if api_url is None else None

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

    def fix_sov_async_check_progress(self, sovid_or_start_ret) -> FixSOVResponse:
        if isinstance(sovid_or_start_ret, dict):
            sov_id = sovid_or_start_ret["id"]
        else:
            sov_id = sovid_or_start_ret

        status_url = self.api_url + f"/api/v1/sov/{sov_id}?include_progress=true"
        # params = {"id": sov_id}

        response = self.session.get(status_url)
        # pprint.pprint(response.json())
        raise_for_status(response)

        response_data: FixSOVResponse = response.json()
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
