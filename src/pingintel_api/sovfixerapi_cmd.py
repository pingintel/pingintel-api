#!/usr/bin/env python

# Copyright 2021-2024 Ping Data Intelligence

import logging
import pathlib
import pprint
import time
from timeit import default_timer as timer
from typing import Literal

import click

from pingintel_api import SOVFixerAPIClient

logger = logging.getLogger(__name__)


global start_time
start_time = None


"""
sovfixerapi.py

Example Python commandline script for using the Ping Data Technologies sovfixer API to process SOVs.
"""


@click.group()
@click.option(
    "-e",
    "--environment",
    type=click.Choice(
        [
            "prod",
            "prodeu",
            "staging",
            "dev",
        ],
        case_sensitive=False,
    ),
)
@click.option(
    "-u",
    "--api-url",
    help="Provide base url (instead of environment, primarily for debugging)",
)
@click.option(
    "--auth-token",
    help="Provide auth token via --auth-token or PINGVISION_AUTH_TOKEN environment variable.",
)
@click.pass_context
def cli(ctx, environment, api_url, auth_token):
    ctx.ensure_object(dict)
    ctx.obj["environment"] = environment
    ctx.obj["auth_token"] = auth_token
    ctx.obj["api_url"] = api_url


def get_client(ctx) -> SOVFixerAPIClient:
    environment = ctx.obj["environment"]
    auth_token = ctx.obj["auth_token"]
    api_url = ctx.obj["api_url"]
    client = SOVFixerAPIClient(
        environment=environment, auth_token=auth_token, api_url=api_url
    )
    return client


# def log(msg):
#     global start_time
#     if start_time is None:
#         start_time = timer()
#     elapsed = timer() - start_time
#     timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
#     click.echo(f"[{timestamp} T+{elapsed:.1f}s] {msg}")


@cli.command()
@click.pass_context
@click.argument(
    "filename", nargs=-1, required=True, type=click.Path(exists=True, dir_okay=False)
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
def fix(
    ctx,
    filename,
    document_type,
    callback_url,
    output_format,
    client_ref,
    write,
):

    if isinstance(filename, pathlib.PosixPath):
        filename = [str(filename)]

    client = get_client(ctx)
    for fn in filename:
        client.fix_sov(
            fn,
            document_type=document_type,
            callback_url=callback_url,
            actually_write=write,
            output_formats=output_format,
            client_ref=client_ref,
        )


@cli.command()
@click.pass_context
@click.option("--cursor-id", "--sovid", help="Cursor ID to start from")
@click.option("--prev-cursor-id")
@click.option("-l", "--page-size", "--limit", default=50)
@click.option("--fields", multiple=True)
@click.option("--search", help="Filter key fields by an arbitrary string")
@click.option("--origin", type=click.Choice(["api", "email"]))
@click.option("--status", type=click.Choice(["P", "I", "E", "R", "C", "F"]))
@click.option("--organization__short_name")
def activity(
    ctx,
    cursor_id=None,
    prev_cursor_id=None,
    page_size=50,
    fields: list[str] | None = None,
    search=None,
    origin: Literal["api", "email"] | None = None,
    status: Literal["P", "I", "E", "R", "C", "F"] | None = None,
    organization__short_name=None,
):
    client = get_client(ctx)
    results = client.list_activity(
        cursor_id=cursor_id,
        prev_cursor_id=prev_cursor_id,
        page_size=page_size,
        fields=fields,
        search=search,
        origin=origin,
        status=status,
        organization__short_name=organization__short_name,
    )
    pprint.pprint(results)


def main():
    cli()


if __name__ == "__main__":
    main()
