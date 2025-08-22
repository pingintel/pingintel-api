#!/usr/bin/env python

# Copyright 2021-2024 Ping Data Intelligence

import logging
import pprint
import time
from timeit import default_timer as timer
import click

from pingintel_api import PingMapsAPIClient

from pingintel_api.api_client_base import AuthTokenNotFound
from pingintel_api.pingdata.types import SOURCES, Location
from pingintel_api.utils import set_verbosity

logger = logging.getLogger(__name__)


global start_time
start_time = None


"""
pingmapsapi.py

Example Python commandline script for using the Ping Data Technologies Data API to access the maps API.
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
    help="Provide auth token via --auth-token or PINGDATA_AUTH_TOKEN environment variable.",
)
@click.option(
    "-v", "--verbose", count=True, help="Can be used multiple times. -v for INFO, -vv for DEBUG, -vvv for very DEBUG."
)
@click.option(
    "-D",
    "--delegate-to",
    metavar="ORG_SHORT_NAME",
    help="Delegate to another organization. Provide the 'short name' of the desired delegatee.  Requires the `delegate` permission.",
)
@click.pass_context
def cli(ctx, environment, api_url, auth_token, verbose, delegate_to):
    ctx.ensure_object(dict)
    ctx.obj["environment"] = environment
    ctx.obj["auth_token"] = auth_token
    ctx.obj["api_url"] = api_url
    ctx.obj["delegate_to"] = delegate_to
    set_verbosity(verbose)


def get_client(ctx) -> PingMapsAPIClient:
    environment = ctx.obj["environment"]
    auth_token = ctx.obj["auth_token"]
    api_url = ctx.obj["api_url"]
    try:
        client = PingMapsAPIClient(environment=environment, auth_token=auth_token, api_url=api_url)
    except AuthTokenNotFound as e:
        click.echo(e)
        raise click.Abort()

    return client


@cli.command()
@click.pass_context
def settings(ctx: click.Context):
    """Get current user's settings."""

    client = get_client(ctx)

    response_data = client.get_settings()
    click.echo(f"+ Finished querying with result:\n{pprint.pformat(response_data)}")


def main():
    cli()


if __name__ == "__main__":
    main()
