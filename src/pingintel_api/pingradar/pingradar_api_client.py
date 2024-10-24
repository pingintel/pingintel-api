#!/usr/bin/env python

# Copyright 2021-2024 Ping Data Intelligence

import urllib.parse

import logging
import os
import pathlib
import pprint
import time
from timeit import default_timer as timer
from typing import BinaryIO, TypedDict, overload

from pingintel_api.api_client_base import APIClientBase

from .. import constants as c
from ..utils import is_fileobj, log, raise_for_status
from . import types as t

logger = logging.getLogger(__name__)


class PingRadarAPIClient(APIClientBase):
    api_subdomain = "radar"
    api_base_domain = "pingintel.com"
    auth_token_env_name = "PINGRADAR_AUTH_TOKEN"
    product = "pingradar"

    def create_submission(
        self, filepaths: list[str | pathlib.Path], client_ref: str | None = None
    ) -> t.PingRadarCreateSubmissionResponse:
        url = self.api_url + "/api/v1/submission"

        multiple_files: (
            list[tuple[str, tuple[str, BinaryIO]]] | dict[str, tuple[str, BinaryIO]]
        ) = []
        for filepath in filepaths:
            files = ("files", (os.path.basename(filepath), open(filepath, "rb")))
            multiple_files.append(files)
        if len(filepaths) == 1:
            multiple_files = {"files": multiple_files[0][1]}

        data = {}
        if client_ref:
            data["client_ref"] = client_ref
        response = self.post(url, files=multiple_files, data=data)

        if len(filepaths) == 1:
            multiple_files["files"][1].close()
        else:
            for file in multiple_files:
                file[1][1].close()
        raise_for_status(response)

        log(f"Submission created: {response.json()}")
        response_data = response.json()
        return response_data

    def get_submission_detail(
        self, pingid: str
    ):  # -> t.PingRadarSubmissionDetailResponse:
        url = self.api_url + f"/api/v1/submission/{pingid}"

        response = self.get(url)

        raise_for_status(response)

        response_data = response.json()
        return response_data

    def list_submission_activity(
        self,
        id: str | None = None,
        cursor_id: str | None = None,
        prev_cursor_id: str | None = None,
        page_size: int | None = None,
        fields: list[str] | None = None,
        search: str | None = None,
        organization__short_name: str | None = None,
    ) -> t.PingRadarListActivityResponse:
        url = self.api_url + "/api/v1/submission"

        kwargs = {}
        if id:
            kwargs["id"] = id
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
    def download_document(self, output_path_or_stream, document_url: str): ...

    @overload
    def download_document(self, output_path_or_stream, pingid: str, filename: str): ...

    def download_document(
        self, output_path_or_stream, document_url=None, pingid=None, filename=None
    ):
        if not document_url:
            encoded_filename = urllib.parse.quote(filename)
            document_url = f"/api/v1/submission/{pingid}/document/{encoded_filename}"

        assert document_url.startswith("/")

        url = self.api_url + document_url
        response = self.get(url)
        raise_for_status(response)

        if is_fileobj(output_path_or_stream):
            output_path_or_stream.write(response.content)
        else:
            with open(output_path_or_stream, "wb") as f:
                f.write(response.content)
