#!/usr/bin/env python

# Copyright 2021-2024 Ping Data Intelligence

import os
import pathlib
import pprint
import time
from typing import IO, Collection, Literal
from datetime import timedelta, datetime
from uuid import UUID
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
        delegate_to_team: UUID | str | int | None = None,
        update_callback_url=None,
        allow_ping_data_api=None,
        workflow=None,
        skip_prior_update_reuse: bool = False,
        company: str | None = None,
        team: str | None = None,
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
        if delegate_to_team is not None:
            data["delegate_to_team"] = delegate_to_team
        if allow_ping_data_api is not None:
            data["allow_ping_data_api"] = allow_ping_data_api
        if workflow is not None:
            data["workflow"] = workflow
        if company is not None:
            data["company"] = company
        if team is not None:
            data["team"] = team

        data["skip_prior_update_reuse"] = skip_prior_update_reuse

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
        delegate_to_team: UUID | str | int | None = None,
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
            elif request_status in t.INCOMPLETE_STATUSES:
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

    def list_history(
        self,
        cursor_id=None,
        page_size=50,
        start: datetime | None = None,
    ) -> t.HistoryResponse:
        url = self.api_url + "/api/v1/sov/history"
        parameters = {}
        if cursor_id:
            parameters["cursor_id"] = cursor_id
        if page_size:
            parameters["page_size"] = page_size
        if start:
            if isinstance(start, datetime):
                start_str = start.strftime("%Y%m%d%H%M%S")
            else:
                start_str = str(start)
            parameters["start"] = start_str

        response = self.get(url, params=parameters)
        raise_for_status(response)

        json = response.json()
        for activity in json.get("results", []):
            activity["completed_time"] = datetime.strptime(activity["completed_time"], "%Y-%m-%dT%H:%M:%S.%fZ")
        return json

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
        company__short_name: str | list[str] | None = None,
        division__short_name: str | list[str] | None = None,
        pingid: str | None = None,
        completed_time__gt: str | None = None,
        completed_time__gte: str | None = None,
        completed_time__lt: str | None = None,
        completed_time__lte: str | None = None,
    ) -> t.ActivityResponse:
        """List activity in the SOV Fixer system.

        id: filter by sovid.
        cursor_id: pagination cursor from a previous response.
        prev_cursor_id: reverse pagination cursor.
        page_size: max results per page (default 50, max 250).
        fields: list of field names to include on each result.
        search: global case-insensitive search substring.
        origin: filter by "api" or "email".
        status: filter by status
        company__short_name: filter by company short name(s).
        division__short_name: filter by division short name(s).
        pingid: filter by Ping ID.
        completed_time__gt/gte/lt/lte: filter by completed_time (format: YYYYMMDDHHmmss, UTC).
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
        if company__short_name:
            parameters["company__short_name"] = company__short_name
        if division__short_name:
            parameters["division__short_name"] = division__short_name
        if pingid:
            parameters["pingid"] = pingid
        if completed_time__gt:
            parameters["completed_time__gt"] = completed_time__gt
        if completed_time__gte:
            parameters["completed_time__gte"] = completed_time__gte
        if completed_time__lt:
            parameters["completed_time__lt"] = completed_time__lt
        if completed_time__lte:
            parameters["completed_time__lte"] = completed_time__lte

        url = self.api_url + "/api/v1/sov/activity"
        response = self.get(url, params=parameters)
        raise_for_status(response)
        return response.json()

    def update_sov_async_init(
        self,
        sovid: str,
        client_ref: str | None = None,
        update_type: str | None = None,
        callback_url: str | None = None,
        username: str | None = None,
        delegate_to_team: UUID | str | int | None = None,
    ) -> t.SOVUpdateAsyncAPIInitResponse:
        if not sovid:
            raise ValueError("Invalid sovid.")
        url = self.api_url + f"/api/v1/sov/{sovid}/initiate_update"

        data: t.SOVUpdateInitiateRequest = {}
        if client_ref:
            data["client_ref"] = client_ref
        if update_type:
            data["update_type"] = update_type
        if callback_url:
            data["callback_url"] = callback_url
        if username:
            data["username"] = username
        if delegate_to_team is not None:
            data["delegate_to_team"] = delegate_to_team

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
        delegate_to_team: UUID | str | int | None = None,
    ) -> t.SOVUpdateAsyncAPIResponse:
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
        if delegate_to_team is not None:
            data["delegate_to_team"] = delegate_to_team

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
        outputter_name: str | None = None,
        output_formats=None,
        metadata=None,
        integrations=None,
        delegate_to_team: UUID | str | int | None = None,
    ) -> t.SOVUpdateAsyncAPIResponse:
        url = self.api_url + f"/api/v1/sov/update/{sudid}/start"
        data: dict = {}
        data["extra_data"] = extra_data or {}
        if policy_terms:
            data["policy_terms"] = policy_terms
        if outputter_name:
            data["outputter_name"] = outputter_name
        if output_formats:
            data["output_formats"] = output_formats
        if metadata:
            data["metadata"] = metadata
        if integrations is not None:
            data["integrations"] = integrations
        if delegate_to_team is not None:
            data["delegate_to_team"] = delegate_to_team

        response = self.post(url, json=data)
        if 200 <= response.status_code < 300:
            pass
            # pprint.pprint(response.json())
        else:
            self.logger.warning(f"Error starting SOV Fixer update request:\n{pprint.pformat(response.text)}")

        raise_for_status(response)

        response_data = response.json()
        return response_data

    def update_sov_async_check_progress(self, sudid) -> t.SOVUpdateResponse:
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
        outputter_name: str | None = None,
        output_formats=None,
        actually_write=False,
        update_type=None,
        callback_url=None,
        noinput=True,
        metadata=None,
        integrations=None,
        delegate_to_team: UUID | str | int | None = None,
        wait_for_completion: bool = True,
    ) -> str:
        if actually_write and not wait_for_completion:
            raise ValueError("Cannot use actually_write=True with wait_for_completion=False")

        client = self
        init_response = client.update_sov_async_init(
            sovid, update_type=update_type, callback_url=callback_url, delegate_to_team=delegate_to_team
        )
        sudid = init_response["id"]
        # print(init_response)
        for location_filename in location_filenames:
            client.update_sov_async_add_locations(
                sudid,
                location_filename,
                delegate_to_team=delegate_to_team,
            )
        start_response = client.update_sov_async_start(
            sudid,
            extra_data=extra_data,
            policy_terms=policy_terms,
            outputter_name=outputter_name,
            output_formats=output_formats,
            metadata=metadata,
            integrations=integrations,
            delegate_to_team=delegate_to_team,
        )

        if not wait_for_completion:
            return sudid

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
            raise RuntimeError("SOV Update failed.")

    def get_or_create_output_async_start(
        self,
        sovid_or_sud: str,
        output_format: str,
        revision: int = -1,
        overwrite_existing: bool = False,
        delegate_to_team: UUID | str | int | None = None,
    ):
        url = self.api_url + f"/api/v1/sov/{sovid_or_sud}/get_or_create_output"
        data = {}
        if output_format:
            data["output_format"] = output_format
        if revision is not None:
            data["revision"] = revision
        if overwrite_existing:
            data["overwrite_existing"] = overwrite_existing
        if delegate_to_team is not None:
            data["delegate_to_team"] = delegate_to_team

        response = self.post(url, data=data)
        raise_for_status(response)
        return response.json()

    def get_or_create_output_async_check_progress(self, output_request_id: str):
        url = self.api_url + f"/api/v1/sov/get_or_create_output/{output_request_id}"
        response = self.get(url)
        raise_for_status(response)
        return response.json()

    def get_or_create_output(
        self,
        sovid_or_sud: str,
        output_format: str,
        revision: int = -1,
        overwrite_existing=False,
        timeout: timedelta | None = timedelta(minutes=5),
        delegate_to_team: UUID | str | int | None = None,
    ) -> t.OutputData:
        """Synchronously get or create an output from a SOV Fixer request. If it exists, it will return immediately.
        If it does not exist, it will start the generation process and poll for completion, then return it."""
        client = self

        start_response = client.get_or_create_output_async_start(
            sovid_or_sud,
            output_format,
            revision,
            overwrite_existing,
            delegate_to_team,
        )

        request_status = start_response["request"]["status"]
        output_request_id = start_response["request"]["id"]
        if request_status == "COMPLETE" or request_status == "FAILED":
            response_data = start_response
        else:
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

    def fetch_sov_output(self, sov_id: str, filename: str, output_path: str | None = None) -> bytes:
        """
        Download an output file from a completed SOV parsing job.

        :param sov_id: The SOV job ID.
        :param filename: The output filename (from result.outputs[].filename).
        :param output_path: If provided, write the result to this local file path.
        :return: Raw response bytes.
        """
        url = self.api_url + f"/api/v1/sov/{sov_id}/output/{filename}"
        response = self.get(url)
        raise_for_status(response)
        if output_path:
            with open(output_path, "wb") as fd:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    fd.write(chunk)
        return response.content

    def get_history_item(self, id: str) -> t.SOVHistoryResponse:
        """
        Get a specific historical SOV or SOV Update by its ID.

        :param id: SOV ID (sovid) or SOV Update ID (sudid).
        :return: Historical SOV data including outputs.
        """
        url = self.api_url + f"/api/v1/sov/history/{id}"
        response = self.get(url)
        raise_for_status(response)
        return response.json()

    def get_building(self, item_key: str) -> dict:
        """
        Retrieve a specific building by its item key.

        :param item_key: Unique building identifier, e.g. "i-s-e-xxxxxxx!SOV!1".
        :return: Building data dict.
        """
        url = self.api_url + f"/api/v1/building/{item_key}"
        response = self.get(url)
        raise_for_status(response)
        return response.json()

    def list_output_formats(
        self,
        sovid: str | None = None,
        division_uuid: str | None = None,
        team_uuid: str | None = None,
    ) -> t.OutputFormatsResponse:
        """List available output formats for the given context."""
        url = self.api_url + "/api/v1/output_formats"
        params = {}
        if sov_id:
            params["sovid"] = sovid
        if division_uuid:
            params["division_uuid"] = division_uuid
        if team_uuid:
            params["team_uuid"] = team_uuid
        response = self.get(url, params=params)
        raise_for_status(response)
        return response.json()

    def get_public_shareable_url(self, sovid: str) -> t.GetPublicShareableUrlResponse:
        """
        Get a publicly shareable Ping.Maps URL for the given SOV.

        :param sovid: The SOV ID.
        :return: Dict with a "url" key containing the shareable URL.
        """
        url = self.api_url + f"/api/v1/pli/policy/{sovid}/get_public_shareable_url"
        response = self.get(url)
        raise_for_status(response)
        return response.json()

    def create_submission(
        self,
        document_type: str = "SOV",
        client_ref: str | None = None,
        extra_data: dict | None = None,
        filename: str | None = None,
    ) -> t.CreateSubmissionResponse:
        """
        Create a new empty submission. Follow with update_sov_async_add_locations then update_sov_async_start.

        :param document_type: "SOV", "PREM_BDX", "CLAIM_BDX", or "SOV_BDX". Default "SOV".
        :param client_ref: Optional user reference identifier.
        :param extra_data: Optional dict of extra_data_* fields (e.g. insured_name, inception_date).
        :param filename: Optional filename for the submission.
        :return: Dict with "id" (int) and "message".
        """
        url = self.api_url + "/api/v1/submission"
        data: dict = {"document_type": document_type}
        if client_ref:
            data["client_ref"] = client_ref
        if extra_data:
            for k, v in extra_data.items():
                data["extra_data_" + k] = v
        if filename:
            data["filename"] = filename
        response = self.post(url, data=data)
        raise_for_status(response)
        return response.json()
