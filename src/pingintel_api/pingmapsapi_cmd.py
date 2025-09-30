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
    "--delegate-to-team",
    metavar="TEAM_ID or TEAM_UUID",
    help="Delegate to a specific team. Provide either the numeric ID or UUID of the target team.",
)
@click.option(
    "--delegate-to-company",
    metavar="COMPANY_ID or COMPANY_UUID",
    help="Delegate to a specific company. Provide either the numeric ID or UUID of the target company.",
)
@click.pass_context
def cli(ctx, environment, api_url, auth_token, verbose, delegate_to_team, delegate_to_company):
    ctx.ensure_object(dict)
    ctx.obj["environment"] = environment
    ctx.obj["auth_token"] = auth_token
    ctx.obj["api_url"] = api_url
    ctx.obj["delegate_to_team"] = delegate_to_team
    ctx.obj["delegate_to_company"] = delegate_to_company
    set_verbosity(verbose)


def get_client(ctx) -> PingMapsAPIClient:
    environment = ctx.obj["environment"]
    auth_token = ctx.obj["auth_token"]
    api_url = ctx.obj["api_url"]
    delegate_to_team = ctx.obj["delegate_to_team"] 
    delegate_to_company = ctx.obj["delegate_to_company"] 
    try:
        client = PingMapsAPIClient(
            environment=environment, 
            auth_token=auth_token, 
            api_url=api_url, 
            delegate_to_team=delegate_to_team, 
            delegate_to_company=delegate_to_company
        )
    except AuthTokenNotFound as e:
        click.echo(e)
        raise click.Abort()

    return client


@cli.command()
@click.pass_context
def settings(ctx: click.Context):
    """Get current user's settings."""

    client = get_client(ctx)

    response_data = client.get_settings(delegate_to_team=client.delegate_to_team,delegate_to_company=client.delegate_to_company)
    click.echo(f"+ Finished querying with result:\n{pprint.pformat(response_data)}")


def main():
    cli()


if __name__ == "__main__":
    main()
