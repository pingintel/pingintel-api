#!/usr/bin/env python

# Copyright 2021-2024 Ping Data Intelligence

import datetime
import urllib.parse

import logging
import os
import pathlib
import pprint
import time
from timeit import default_timer as timer
from typing import BinaryIO, TypedDict, overload, List
from typing import BinaryIO, TypedDict, Unpack, overload

from pingintel_api.api_client_base import APIClientBase

from .. import constants as c
from ..utils import is_fileobj, raise_for_status
from . import types as t

logger = logging.getLogger(__name__)


class PingVisionAPIClient(APIClientBase):
    api_subdomain = "vision"
    api_base_domain = "pingintel.com"
    auth_token_env_name = "PINGVISION_AUTH_TOKEN"
    product = "pingvision"

    def create_submission(
        self,
        filepaths: list[str | pathlib.Path],
        team_uuid: str | None = None,
        client_ref: str | None = None,
        insured_name: str | None = None,
        inception_date: datetime.date | None = None,
        expiration_date: datetime.date | None = None,
        delegate_to_team: str | None = None,
    ) -> t.PingVisionCreateSubmissionResponse:
        """
        Initiate a new submission from one or more original files.

        :param filepaths: List of file paths to submit.
        :type filepaths: list[str|pathlib.Path]

        :param team_uuid: UUID of the team to which the submission should be sent. Required if the API user has access to create submissions for multiple teams.
        :type team_uuid: str|None

        :param client_ref: (Optional) Client reference string.
        :type client_ref: str|None

        :param insured_name: (Optional) Name of the insured.
        :type insured_name: str|None

        :param inception_date: (Optional) Inception date of the submission.
        :type inception_date: datetime.date|None

        :param expiration_date: (Optional) Expiration date of the submission.
        :type expiration_date: datetime.date|None

        :param delegate_to_team: (Optional) Requires delegation permissions. Allows the user to assume the role of a user in another team.
        :type delegate_to_team: str|None
        """

        url = self.api_url + "/api/v1/submission"

        multiple_files: list[tuple[str, tuple[str, BinaryIO]]] | dict[str, tuple[str, BinaryIO]] = []
        for filepath in filepaths:
            files = ("files", (os.path.basename(filepath), open(filepath, "rb")))
            multiple_files.append(files)
        if len(filepaths) == 1:
            multiple_files = {"files": multiple_files[0][1]}

        data = {}
        if client_ref:
            data["client_ref"] = client_ref
        if insured_name:
            data["insured_name"] = insured_name
        if team_uuid:
            data["team_uuid"] = team_uuid
        if inception_date:
            data["inception_date"] = inception_date.isoformat()
        if expiration_date:
            data["expiration_date"] = expiration_date.isoformat()
        if delegate_to_team:
            data["delegate_to_team"] = delegate_to_team

        response = self.post(url, files=multiple_files, data=data)

        if len(filepaths) == 1:
            multiple_files["files"][1].close()
        else:
            for file in multiple_files:
                file[1][1].close()
        raise_for_status(response)

        self.logger.info(f"Submission created: {response.json()}")
        response_data = response.json()
        return response_data

    def get_submission_detail(self, pingid: str):  # -> t.PingVisionSubmissionDetailResponse:
        url = self.api_url + f"/api/v1/submission/{pingid}/history"

        response = self.get(url)

        raise_for_status(response)

        response_data = response.json()
        return response_data

    def list_submission_activity(
        self,
        pingid: str | None = None,
        cursor_id: str | None = None,
        prev_cursor_id: str | None = None,
        page_size: int | None = None,
        fields: list[str] | None = None,
        search: str | None = None,
        organization__short_name: str | None = None,
    ) -> t.PingVisionListActivityResponse:
        url = self.api_url + "/api/v1/submission"

        kwargs = {}
        if pingid:
            kwargs["id"] = pingid
        if cursor_id:
            kwargs["cursor_id"] = cursor_id
        if prev_cursor_id:
            kwargs["prev_cursor_id"] = prev_cursor_id
        if page_size:
            kwargs["page_size"] = page_size
        if fields:
            kwargs["fields"] = fields
        if search:
            kwargs["search"] = search
        if organization__short_name:
            kwargs["organization__short_name"] = organization__short_name

        response = self.get(url, params=kwargs)

        raise_for_status(response)

        response_data = response.json()
        return response_data

    @overload
    def download_document(self, output_path_or_stream, *, document_url: str) -> None: ...

    @overload
    def download_document(self, output_path_or_stream, *, pingid: str, filename: str) -> None: ...

    def download_document(self, output_path_or_stream, document_url=None, pingid=None, filename=None) -> None:
        if not document_url:
            encoded_filename = urllib.parse.quote(filename)
            document_url = f"/api/v1/submission/{pingid}/document/{encoded_filename}"

        if document_url.startswith("http"):
            url = document_url
        else:
            url = self.api_url + document_url
        
        assert url.startswith(self.api_url), f"document_url should start with {self.api_url} or / but got {url}"

        response = self.get(url)
        raise_for_status(response)

        if is_fileobj(output_path_or_stream):
            output_path_or_stream.write(response.content)
        else:
            with open(output_path_or_stream, "wb") as f:
                f.write(response.content)

    def list_submission_statuses(self, division: str) -> list[t.PingVisionListSubmissionStatusItemResponse]:
        url = self.api_url + f"/api/v1/submission-status"

        response = self.get(url, params={"division": division})
        raise_for_status(response)

        response_data = response.json()
        return response_data

    def change_status(self, pingid: str, workflow_status_id: int) -> t.PingVisionChangeSubmissionStatusResponse:
        url = self.api_url + f"/api/v1/submission/{pingid}/change_status"

        data = {
            "workflow_status_uuid": workflow_status_id,
        }
        response = self.patch(url, json=data)
        raise_for_status(response)
        response_data = response.json()
        return response_data

    def bulk_update_submission(
        self, pingids: list[str], changes: List[t.PingVisionSubmissionBulkUpdateChangeItem]
    ) -> List[t.PingVisionSubmissionBulkUpdateResponse]:
        url = self.api_url + f"/api/v1/submission/bulkupdate"

        data = {
            "ids": pingids,
            "changes": changes,
        }
        response = self.post(url, json=data)
        raise_for_status(response)
        response_data = response.json()
        return response_data

    def update_submission(self, pingid: str, data: dict):
        url = self.api_url + f"pi/v1/submission/{pingid}"

        response = self.patch(url, json=data)
        raise_for_status(response)
        response_data = response.json()
        return response_data

    def list_submission_events(
        self,
        **kwargs: Unpack[t.PingVisionSubmissionEventsRequest],
    ) -> t.PingVisionSubmissionEventsResponse:
        url = self.api_url + f"/api/v1/submission-events"

        pingid = kwargs.get("pingid")
        division = kwargs.get("division")
        team = kwargs.get("team")
        start = kwargs.get("start")
        cursor_id = kwargs.get("cursor_id")
        page_size = kwargs.get("page_size")

        params = {}
        if pingid:
            params["pingid"] = pingid
        if division:
            params["division"] = division
        if team:
            params["team"] = team
        if start:
            params["start"] = start.strftime("%Y%m%d%H%M%S")
        if cursor_id:
            params["cursor_id"] = cursor_id
        if page_size:
            params["page_size"] = page_size

        response = self.get(url, params=params)
        raise_for_status(response)

        response_data = response.json()
        return response_data

    def list_teams(self) -> list[t.PingVisionTeamsResponse]:
        url = self.api_url + "/api/v1/user/teams"
        response = self.get(url)
        raise_for_status(response)

        response_data = response.json()
        return response_data

    def add_data_items(self, pingid: str, action: t.DATA_ITEM_ACTIONS, items: dict[str, str | int | float | bool]):
        url = self.api_url + f"/api/v1/submission/{pingid}/add_data_items"
        response = self.post(url, json={"items": items, "action": action})
        raise_for_status(response)
