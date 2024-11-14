#!/usr/bin/env python

# Copyright 2021-2024 Ping Data Intelligence

import logging
import pprint
import time
from timeit import default_timer as timer
import click

from pingintel_api import PingDataAPIClient

from pingintel_api.api_client_base import AuthTokenNotFound
from pingintel_api.pingdata.types import SOURCES, Location
from pingintel_api.utils import set_verbosity

logger = logging.getLogger(__name__)


global start_time
start_time = None


"""
pingdataapi.py

Example Python commandline script for using the Ping Data Technologies Data API to enhance locations with additional data.
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
    help="Provide auth token via --auth-token or PINGDSTS_AUTH_TOKEN environment variable.",
)
@click.option(
    "-v", "--verbose", count=True, help="Can be used multiple times. -v for INFO, -vv for DEBUG, -vvv for very DEBUG."
)
@click.pass_context
def cli(ctx, environment, api_url, auth_token, verbose):
    ctx.ensure_object(dict)
    ctx.obj["environment"] = environment
    ctx.obj["auth_token"] = auth_token
    ctx.obj["api_url"] = api_url
    set_verbosity(verbose)


def get_client(ctx) -> PingDataAPIClient:
    environment = ctx.obj["environment"]
    auth_token = ctx.obj["auth_token"]
    api_url = ctx.obj["api_url"]
    try:
        client = PingDataAPIClient(environment=environment, auth_token=auth_token, api_url=api_url)
    except AuthTokenNotFound as e:
        click.echo(e)
        raise click.Abort()

    return client


@cli.command()
@click.pass_context
@click.option("-a", "--address", multiple=True)
@click.option(
    "-s",
    "--sources",
    multiple=True,
    type=click.Choice(SOURCES.get_options(), case_sensitive=False),
    required=True,
)
@click.option("-c", "--country", type=str, default=None, help="Optional. Provides a country hint to the geocoders.")
@click.option("--latitude", type=float, default=None, help="Optional. Specify latitude.")
@click.option("--longitude", type=float, default=None, help="Optional. Specify longitude.")
@click.option("--timeout", type=float, default=None, help="Optional. Maximum time to wait for response in seconds.")
@click.option("-r", "--include-raw-response", is_flag=True, help="Optional. Include raw response from all sources.")
@click.option("--nocache", is_flag=True, help="If set, do not use cache.")
def enhance(
    ctx: click.Context,
    address: str,
    sources: list[str],
    country: str | None,
    latitude: float | None,
    longitude: float | None,
    timeout: float | None = None,
    include_raw_response: bool = False,
    nocache: bool = False,
    # extra_location_kwargs: dict | None = None,
):
    # if not extra_location_kwargs:
    #     extra_location_kwargs = {}

    client = get_client(ctx)

    response_data = client.enhance(
        address=address,
        country=country,
        latitude=latitude,
        longitude=longitude,
        sources=sources,
        timeout=timeout,
        include_raw_response=include_raw_response,
        nocache=nocache,
    )
    click.echo(f"+ Finished querying with result:\n{pprint.pformat(response_data)}")


@cli.command()
@click.pass_context
@click.option("-a", "--address", multiple=True)
@click.option("-f", "--file", type=click.File("r"), help="File containing location data, one per line.")
@click.option(
    "-s",
    "--sources",
    multiple=True,
    type=click.Choice(SOURCES.get_options(), case_sensitive=False),
    # required=True,
)
@click.option("--timeout", type=float, default=None, help="Optional. Maximum time to wait for response in seconds.")
@click.option("-r", "--include-raw-response", is_flag=True, help="Optional. Include raw response from all sources.")
@click.option("--nocache", is_flag=True, help="If set, do not use cache.")
@click.option("--fetch-outputs/--no-fetch-outputs", is_flag=True, default=True)
@click.option("-v", "--verbose", help="Enable verbose output. Can be used up to 3 times.", count=True)
def bulk_enhance(
    ctx: click.Context,
    address: list[str],
    file: click.File,
    sources: list[str],
    timeout: float | None,
    include_raw_response: bool,
    nocache: bool,
    fetch_outputs: bool,
    verbose: int,
):
    client = get_client(ctx)

    locations = []
    address_id_ctr = 0
    if address:
        for addr in address:
            address_id_ctr += 1
            locations.append(Location(address=addr, id=f"id_{address_id_ctr:03d}"))

    if file:
        for line in file:
            address_id_ctr += 1
            locations.append(Location(address=line.strip(), id=f"id_{address_id_ctr:03d}"))

    response_data = client.bulk_enhance(
        locations=locations,
        sources=sources,
        timeout=timeout,
        include_raw_response=include_raw_response,
        nocache=nocache,
        fetch_outputs=fetch_outputs,
        verbose=verbose,
    )
    click.echo(f"+ Finished querying with result:\n{pprint.pformat(response_data)}")


def main():
    cli()


if __name__ == "__main__":
    main()
