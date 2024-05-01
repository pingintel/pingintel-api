#!/usr/bin/env python

# Copyright 2021-2024 Ping Data Intelligence

import base64
import enum
import gzip
import hashlib
import io
import json
import logging
import os
import pathlib
import pprint
import random
import time
import zipfile
from timeit import default_timer as timer

import click
import requests
from requests.exceptions import HTTPError

from pingintel_api.sov_fixer_api_client import fix_sov

logger = logging.getLogger(__name__)


global start_time
start_time = None


"""
sovfixerapi.py

Example Python commandline script for using the Ping Data Technologies sovfixer API to process SOVs.
"""


def log(msg):
    global start_time
    if start_time is None:
        start_time = timer()
    elapsed = timer() - start_time
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    click.echo(f"[{timestamp} T+{elapsed:.1f}s] {msg}")


@click.command()
@click.argument(
    "filename", nargs=-1, required=True, type=click.Path(exists=True, dir_okay=False)
)
@click.option(
    "-e",
    "--environment",
    type=click.Choice(
        [
            "staging",
            "staging2",
            "prod",
            "prod2",
            "prodeu",
            "prodeu2",
            "local",
            "local2",
            "dev",
            "dev2",
        ],
        case_sensitive=False,
    ),
    default="staging",
)
@click.option(
    "-d",
    "--document-type",
    type=click.Choice(
        ["SOV", "PREM_BDX", "CLAIM_BDX", "SOV_BDX", "ACORD"], case_sensitive=False
    ),
    default="SOV",
    help="Identify `filename` document type.  Defaults to SOV.",
)
@click.option(
    "--auth-token",
    help="Provide auth token via --auth-token or SOVFIXER_AUTH_TOKEN environment variable.",
)
@click.option(
    "--callback-url", help="(Optional) Provide a URL to which results should be POSTed."
)
@click.option(
    "-o",
    "--output-format",
    multiple=True,
    help="Select output format.",
)
@click.option("--client-ref")
@click.option(
    "--write",
    "--no-write",
    is_flag=True,
    default=False,
    help="If set, actually write the output. Otherwise, download as a test but do not write.",
)
def main(
    filename,
    environment,
    document_type,
    auth_token,
    callback_url,
    output_format,
    client_ref,
    write,
):
    if environment == "prod":
        API_URL = "https://api.sovfixer.com"
    elif environment == "prod2":
        API_URL = "https://api2.sovfixer.com"
    elif environment == "prodeu":
        API_URL = "https://api.eu.sovfixer.com"
    elif environment == "local":
        API_URL = "http://api-local.sovfixer.com"
    elif environment == "local2":
        API_URL = "http://localhost:8000"
    else:
        API_URL = f"https://api-{environment}.sovfixer.com"

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
            raise NotImplementedError()
        auth_token = os.environ.get(f"PING_{serverspace}_AUTH_TOKEN".upper())

    if isinstance(filename, pathlib.PosixPath):
        filename = [str(filename)]

    for fn in filename:
        fix_sov(
            API_URL,
            fn,
            document_type,
            auth_token,
            environment,
            callback_url,
            actually_write=write,
            output_formats=output_format,
            client_ref=client_ref,
        )


if __name__ == "__main__":
    main()
