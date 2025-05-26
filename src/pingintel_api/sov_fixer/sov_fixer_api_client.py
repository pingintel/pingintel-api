#!/usr/bin/env python

# Copyright 2021-2024 Ping Data Intelligence

import os
import pathlib
import pprint
import time
from typing import IO, Collection, Literal
from datetime import timedelta
import click

from pingintel_api.api_client_base import APIClientBase

from ..utils import is_fileobj, raise_for_status
from . import types as t


class SOVFixerAPIClient(APIClientBase):
    api_subdomain = "api"
    api_base_domain = "sovfixer.com"
    auth_token_env_name = "SOVFIXER_AUTH_TOKEN"
    product = "sovfixer"
    include_legacy_dashes = True

    SOV_STATUS = t.SOV_STATUS
    SOV_RESULT_STATUS = t.SOV_RESULT_STATUS

    def fix_sov_async_start(
        self,
        file: IO[bytes] | str | pathlib.Path | Collection[IO[bytes] | str | pathlib.Path],
        document_type: str = "SOV",
        filename: str | Collection[str] | None = None,
        callback_url=None,
        output_formats=None,
        client_ref=None,
        integrations=None,
        extra_data=None,
        delegate_to: str | None = None,
        delegate_to_team: str | None = None,
        update_callback_url=None,
        allow_ping_data_api=None,
        workflow=None,
    ):
        """
        Start a SOV Fixer request from one or more files asynchronously.

        :param file: The file to process.  Can be a file object, a path to a file, or a list of file objects or paths.
        :param document_type: The type of document being processed.  Default is "SOV".
        :param filename: The name of the file.  If file is a file object, this is required. If file is a list of file objects, this must be a list of filenames.
        :param callback_url: The URL to call when the request is complete.
        """

        url = self.api_url + "/api/v1/sov"

        files = self._get_files_for_request(file, filename)
        data = {}
        if callback_url:
            data["callback_url"] = callback_url
        if update_callback_url:
            data["update_callback_url"] = update_callback_url
        if document_type:
            data["document_type"] = document_type
        if output_formats:
            data["output_formats"] = output_formats
        if client_ref:
            data["client_ref"] = client_ref
        if integrations is not None:
            data["integrations"] = integrations
        if extra_data is not None:
            for k, v in extra_data.items():
                data["extra_data_" + k] = v
        if delegate_to is not None:
            data["delegate_to"] = delegate_to
        if delegate_to_team is not None:
            data["delegate_to_team"] = delegate_to_team
        if allow_ping_data_api is not None:
            data["allow_ping_data_api"] = allow_ping_data_api
        if workflow is not None:
            data["workflow"] = workflow

        response = self.post(url, files=files, data=data)
        if 200 <= response.status_code < 300:
            # pprint.pprint(response.json())
            pass
        else:
            self.logger.warning(f"Error starting SOV Fixer request:\n{pprint.pformat(response.text)}")

        raise_for_status(response)

        response_data = response.json()
        sov_id = response_data["id"]
        message = response_data["message"]
        status_url = self.api_url + f"/api/v1/sov/{sov_id}"
        self.logger.info(f"+ Dispatched {sov_id}: {message}.  Now, polling for results at {status_url}.")
        return response_data

    def fix_sov_async_check_progress(self, sovid_or_start_ret) -> t.FixSOVResponse:
        if isinstance(sovid_or_start_ret, dict):
            sov_id = sovid_or_start_ret["id"]
        else:
            sov_id = sovid_or_start_ret

        status_url = self.api_url + f"/api/v1/sov/{sov_id}?include_progress=true"
        # params = {"id": sov_id}

        response = self.get(status_url)
        # pprint.pprint(response.json())
        raise_for_status(response)

        response_data: t.FixSOVResponse = response.json()
        # request_status = response_data["request"]["status"]
        return response_data

    def fix_sov_download(
        self,
        output_ret: t.FixSOVResponseResultOutput | t.OutputData,
        output_path=None,
        actually_write=True,
    ):
        """Download one output of a SOV Fixer request.

        output_ret: dict
            Pass it one of the elements of the "outputs" list from the response of fix_sov_async_check_progress.
        output_path: str
            The path to write the file to.  If None, the filename from the output_ret will be used.
        actually_write: bool
            If True, the file will be written to disk.  If False, the file will be downloaded but not written to disk.  This is mostly for testing.
        """

        output_url = output_ret["url"]

        # if output_url does not have the base_url then add it.
        if not output_url.startswith("http"):
            assert output_url.startswith("/"), f"Invalid output URL: {output_url}"
            output_url = self.api_url + output_url

        if self.environment and self.environment == "local2" and "api-local.sovfixer.com" in output_url:
            output_url = output_url.replace("api-local.sovfixer.com", "localhost:8000")

        output_description = output_ret.get("description", output_ret.get("label"))
        output_filename = output_ret.get("filename", output_ret.get("scrubbed_filename"))
        if output_path is None:
            output_path = output_filename

        return self.download_file(
            output_url,
            output_path,
            actually_write=actually_write,
            output_description=output_description,
        )

    def download_file(
        self,
        download_url,
        output_path,
        actually_write=False,
        output_description=None,
    ):
        self.logger.info(f"Requesting output from {download_url}...")
        if download_url.startswith("/"):
            download_url = self.api_url + download_url

        with self.get(download_url, stream=True) as response:
            raise_for_status(response)
            filesize_mb = int(response.headers.get("content-length", 0)) / 1024 / 1024
            # pprint.pprint(dict(response.headers))
            self.logger.info(f"  - Streaming {output_description} output ({filesize_mb:.2f} MB)...")

            if actually_write:
                with open(output_path, "wb") as fd:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        fd.write(chunk)
                self.logger.info(f"  - Downloaded {output_description} output: {output_path}.")
        return output_path if actually_write else None

    def activity_download(self, output_ret, actually_write=False, output_path=None):
        output_url = output_ret["url"]
        is_update_output_ret = "filename" not in output_ret and "scrubbed_filename" not in output_ret
        is_input_ret = "label" not in output_ret and not is_update_output_ret

        # this is old and will go away...
        if is_update_output_ret:
            output_description = "Update"
            output_filename = output_url.split("/")[-1]

        elif is_input_ret:
            output_description = "Input"
            output_filename = output_ret["filename"]
        else:
            output_description = output_ret["label"]
            output_filename = output_ret["scrubbed_filename"]
        if output_path is None:
            output_path = output_filename

        try:
            return self.download_file(
                output_url,
                output_path,
                actually_write=actually_write,
                output_description=output_description,
            )
        except Exception as e:
            self.logger.warning(f"Error downloading {output_description} output: {e}")
            return None

    def fix_sov(
        self,
        filename: list[str | pathlib.Path] | str | pathlib.Path,
        *,
        document_type: str = "SOV",
        callback_url=None,
        actually_write=False,
        output_formats=None,
        integrations=None,
        client_ref=None,
        extra_data=None,
        update_callback_url=None,
        delegate_to=None,
        delegate_to_team=None,
        noinput=True,
        allow_ping_data_api=True,
        workflow=None,
    ) -> t.FixSOVProcessResponse:
        sov_fixer_client = self
        start_response = sov_fixer_client.fix_sov_async_start(
            filename,
            document_type=document_type,
            callback_url=callback_url,
            output_formats=output_formats,
            integrations=integrations,
            client_ref=client_ref,
            extra_data=extra_data,
            update_callback_url=update_callback_url,
            delegate_to=delegate_to,
            delegate_to_team=delegate_to_team,
            allow_ping_data_api=allow_ping_data_api,
            workflow=workflow,
        )

        while 1:
            response_data = sov_fixer_client.fix_sov_async_check_progress(start_response)
            # raise_for_status(response_data)
            # pprint.pprint(response_data)

            request_status = response_data["request"]["status"]
            pct_complete = response_data["request"]["pct_complete"]
            last_status = response_data["request"]["last_health_status"]

            POLL_SECS = 2.5
            if request_status == "PENDING":
                self.logger.info("  - Has not yet been queued for processing.")
                time.sleep(POLL_SECS)
            elif request_status == "IN_PROGRESS":
                self.logger.info(f"  - Still in progress ({pct_complete}% complete): {last_status}")
                time.sleep(POLL_SECS)
            else:
                break

        result_status = response_data["result"]["status"]
        result_message = response_data["result"]["message"]
        self.logger.info(f"+ Finished with result {result_status}: {result_message}")

        local_outputs = None
        if result_status == "SUCCESS":
            self.logger.info("Complete!  Fetching outputs.")
            local_outputs = []
            for output in response_data["result"]["outputs"]:
                output_url = output["url"]
                if self.environment and self.environment == "local2" and "api-local.sovfixer.com" in output_url:
                    output_url = output_url.replace("api-local.sovfixer.com", "localhost:8000")

                output_filename = output["filename"]

                output_path = output_filename

                if actually_write:
                    if os.path.exists(output_path):
                        if not noinput:
                            yesno = input(f"Do you want to overwrite the existing file {output_path} [y/N]? ")
                            if yesno.lower() != "y":
                                continue

                sov_fixer_client.fix_sov_download(
                    output,
                    actually_write=actually_write,
                    output_path=output_path,
                )
                local_outputs.append(output_path)
            return {
                "success": True,
                "id": start_response["id"],
                "start_response": start_response,
                "final_response": response_data,
                "local_outputs": local_outputs,
            }
        else:
            self.logger.warning(f"* Parsing failed!  Raw API output:\n{response_data}")
            return {
                "success": False,
                "id": start_response["id"],
                "start_response": start_response,
                "final_response": response_data,
                "local_outputs": local_outputs,
            }

    def list_activity(
        self,
        id=None,
        cursor_id=None,
        prev_cursor_id=None,
        page_size=50,
        fields: list[str] | None = None,
        search=None,
        origin: Literal["api", "email"] | None = None,
        status: Literal["P", "I", "E", "R", "C", "F"] | None = None,
        organization__short_name=None,
    ) -> t.ActivityResponse:
        """List activity in the SOV Fixer system.
        id: str
            The ID of the activity to retrieve.
        cursor_id: str
            The cursor ID to use for pagination. Do not set on the first call, but provide the value from each previous call to the next to get the next page.
        prev_cursor_id: str
            See cursor_id, but this goes backwards.
        page_size: int
            The number of results to return per page. Default is 50.
        fields: str
            The fields to include in the response. Default is all fields.
        search: str
            A search term to filter results by.
        origin: str
            Filter by the origin of the activity. Can be "api" or "email".
        status: str
            Filter by the status of the activity. Can be "P" (pending), "I" (in progress), "E" (enriching), "R" (re-enriching), "C" (complete), or "F" (failed).
        organization__short_name: str
            Filter by the short name of the organization that created the activity
        """
        parameters = {}
        if id:
            parameters["id"] = id
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
        response = self.get(url, params=parameters)
        raise_for_status(response)
        return response.json()

    def update_sov_async_init(
        self,
        sovid: str,
        client_ref=None,
        update_type: str = None,
        callback_url: str = None,
    ):
        if not sovid:
            raise ValueError("Invalid sovid.")
        url = self.api_url + f"/api/v1/sov/{sovid}/initiate_update"

        data = {}
        if client_ref:
            data["client_ref"] = client_ref
        if update_type:
            data["update_type"] = update_type
        if callback_url:
            data["callback_url"] = callback_url

        response = self.post(url, data=data)
        if 200 <= response.status_code < 300:
            # pprint.pprint(response.json())
            pass
        else:
            self.logger.warning(f"Error starting SOV Fixer update request:\n{pprint.pformat(response.text)}")

        raise_for_status(response)

        response_data = response.json()
        return response_data

    def update_sov_async_add_locations(
        self,
        sudid: str,
        file: IO[bytes] | str,
        filename=None,
    ):
        url = self.api_url + f"/api/v1/sov/update/{sudid}/add_locations"
        if is_fileobj(file):
            if filename is None:
                raise ValueError("Need filename if file is a file object.")

            files = {"file": (filename, file)}
        else:
            if not os.path.exists(file):
                raise click.ClickException(f"Path {file} does not exist.")

            files = {"file": open(file, "rb")}

        data = {}

        response = self.post(url, files=files, data=data)
        if 200 <= response.status_code < 300:
            pass
            # pprint.pprint(response.json())
        else:
            self.logger.warning(f"Error adding locations to SOV Fixer update request:\n{pprint.pformat(response.text)}")

        raise_for_status(response)

        response_data = response.json()
        return response_data

    def update_sov_async_start(
        self,
        sudid: str,
        extra_data=None,
        policy_terms=None,
        policy_terms_format_name=None,
        output_formats=None,
        metadata=None,
    ):
        url = self.api_url + f"/api/v1/sov/update/{sudid}/start"
        data = {}
        if extra_data:
            data["extra_data"] = extra_data
        if policy_terms:
            data["policy_terms"] = policy_terms
        if policy_terms_format_name:
            data["policy_terms_format_name"] = policy_terms_format_name
        if output_formats:
            data["output_formats"] = output_formats
        if metadata:
            data["metadata"] = metadata

        response = self.post(url, json=data)
        if 200 <= response.status_code < 300:
            pass
            # pprint.pprint(response.json())
        else:
            self.logger.warning(f"Error starting SOV Fixer update request:\n{pprint.pformat(response.text)}")

        raise_for_status(response)

        response_data = response.json()
        return response_data

    def update_sov_async_check_progress(self, sudid):
        status_url = self.api_url + f"/api/v1/sov/update/{sudid}"

        response = self.get(status_url)
        # pprint.pprint(response.json())
        raise_for_status(response)

        response_data = response.json()
        return response_data

    def update_sov(
        self,
        sovid,
        location_filenames,
        extra_data=None,
        policy_terms=None,
        policy_terms_format_name=None,
        output_formats=None,
        actually_write=False,
        update_type=None,
        callback_url=None,
        noinput=True,
        metadata=None,
    ):
        client = self
        init_response = client.update_sov_async_init(sovid, update_type=update_type, callback_url=callback_url)
        sudid = init_response["id"]
        # print(init_response)
        for location_filename in location_filenames:
            client.update_sov_async_add_locations(
                sudid,
                location_filename,
            )
        start_response = client.update_sov_async_start(
            sudid,
            extra_data=extra_data,
            policy_terms=policy_terms,
            policy_terms_format_name=policy_terms_format_name,
            output_formats=output_formats,
            metadata=metadata,
        )

        while 1:
            response_data = client.update_sov_async_check_progress(sudid)
            request_status = response_data["request"]["status"]
            POLL_SECS = 2.5
            if request_status == "PENDING":
                self.logger.info("  - Has not yet been queued for processing.")
                time.sleep(POLL_SECS)
            elif request_status == "IN_PROGRESS":
                self.logger.info(f"  - Still in progress: {request_status}")
                time.sleep(POLL_SECS)
            else:
                break

        result_status = response_data["result"]["status"]
        self.logger.info(f"+ Finished with result {result_status}")

        if result_status == "SUCCESS":
            self.logger.info("Complete!  Fetching outputs.")
            for output in response_data["result"]["outputs"]:
                output_url = output["url"]
                if self.environment and self.environment == "local2" and "api-local.sovfixer.com" in output_url:
                    output_url = output_url.replace("api-local.sovfixer.com", "localhost:8000")

                output_filename = output["filename"]

                output_path = output_filename

                if actually_write:
                    if os.path.exists(output_path):
                        if not noinput:
                            yesno = input(f"Do you want to overwrite the existing file {output_path} [y/N]? ")
                            if yesno.lower() != "y":
                                continue

                client.fix_sov_download(
                    output,
                    actually_write=actually_write,
                    output_path=output_path,
                )
            return sudid
        else:
            self.logger.warning(f"* SOV Update failed!  Raw API output:\n{response_data}")
            return False

    def get_or_create_output_async_start(
        self, sovid_or_sud: str, output_format: str, revision: int = -1, overwrite_existing=False
    ):
        url = self.api_url + f"/api/v1/sov/{sovid_or_sud}/get_or_create_output"
        data = {}
        if output_format:
            data["output_format"] = output_format
        if revision is not None:
            data["revision"] = revision
        if overwrite_existing:
            data["overwrite_existing"] = overwrite_existing

        response = self.post(url, data=data)
        raise_for_status(response)
        return response.json()

    def get_or_create_output_async_check_progress(self, output_request_id: str):
        url = self.api_url + f"/api/v1/sov/get_or_create_output/{output_request_id}"
        response = self.get(url)
        return response.json()

    def get_or_create_output(
        self,
        sovid_or_sud: str,
        output_format: str,
        revision: int = -1,
        overwrite_existing=False,
        timeout: timedelta | None = timedelta(minutes=5),
    ) -> t.OutputData:
        """Synchronously get or create an output from a SOV Fixer request. If it exists, it will return immediately.
        If it does not exist, it will start the generation process and poll for completion, then return it."""
        client = self

        start_response = client.get_or_create_output_async_start(
            sovid_or_sud, output_format, revision, overwrite_existing
        )

        output_request_id = start_response["request"]["id"]
        start_time = time.time()
        while 1:
            if timeout and time.time() - start_time > timeout.total_seconds():
                raise TimeoutError(f"Timeout waiting for output generation: {output_request_id}")
            response_data = client.get_or_create_output_async_check_progress(output_request_id)
            request_status = response_data["request"]["status"]
            POLL_SECS = 2.5
            if request_status == "PENDING":
                self.logger.info("  - Has not yet been queued for processing.")
                time.sleep(POLL_SECS)
            elif request_status == "IN_PROGRESS":
                self.logger.info(f"  - Still in progress: {request_status}")
                time.sleep(POLL_SECS)
            else:
                break

        self.logger.info(f"+ Finished with result {response_data.get('result',{}).get('status')}")
        result = response_data.get("result", {})
        if not result:
            raise ValueError(f"Invalid response: {response_data}")
        output = t.OutputData(
            label=result.get("label", None),
            scrubbed_filename=result.get("scrubbed_filename", None),
            output_format=result.get("output_format", None),
            url=result.get("url", None),
            ping_certified_id=result.get("ping_certified_id", None),
        )
        return output

    def add_building(self, sovid: str, building_data):
        url = self.api_url + f"/api/v1/sov/{sovid}/add_building"
        data = {}
        data["building_data"] = building_data
        response = self.post(url, json=data)
        if 200 <= response.status_code < 300:
            # pprint.pprint(response.json())
            pass
        else:
            self.logger.warning(f"Error adding building to SOV:\n{pprint.pformat(response.text)}")

        raise_for_status(response)

        response_data = response.json()
        return response_data
