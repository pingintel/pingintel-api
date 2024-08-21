#!/usr/bin/env python

# Copyright 2021-2024 Ping Data Intelligence

import logging
import pathlib
import pprint
import time
from timeit import default_timer as timer

import click

from pingintel_api import PingVisionAPIClient

logger = logging.getLogger(__name__)


global start_time
start_time = None


"""
pingvisionapi.py

Example Python commandline script for using the Ping Data Technologies Ping Vision API to process SOVs.
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
    "-u", "--api-url",
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


def get_client(ctx) -> PingVisionAPIClient:
    environment = ctx.obj["environment"]
    auth_token = ctx.obj["auth_token"]
    api_url = ctx.obj["api_url"]
    client = PingVisionAPIClient(environment=environment, auth_token=auth_token, api_url=api_url)
    return client

@cli.command()
@click.pass_context
@click.argument(
    "filename", nargs=-1, required=True, type=click.Path(exists=True, dir_okay=False)
)
# @click.option("--client-ref")
@click.option(
    "--poll-until-ready",
    is_flag=True,
    default=False,
    help="If set, poll until the submission is ready.",
)
def create(ctx, filename, poll_until_ready=False):
    if isinstance(filename, pathlib.PosixPath):
        filename = [str(filename)]

    client = get_client(ctx)
    ret = client.create_submission(filepaths=filename)
    pingid = ret["id"]

    if poll_until_ready:
        while True:
            ret = client.get_submission_detail(pingid=pingid)
            pprint.pprint(ret)
            if ret["workflow_status"] == "completed":
                break
            time.sleep(1.0)


@cli.command()
@click.pass_context
@click.argument("pingid", type=str)
def get(ctx, pingid):
    client = get_client(ctx)

    ret = client.get_submission_detail(pingid=pingid)
    pprint.pprint(ret)


@cli.command()
@click.pass_context
@click.option("--pretty", is_flag=True, default=False)
@click.option('-l', '--limit', '--page-size', type=int, default=None, help="Limit the number of results returned.") 
def activity(ctx, pretty, limit):
    client = get_client(ctx)

    results = client.list_submission_activity(page_size=limit)
    if pretty:
        """ print it like a table """
        print(f"{'Activity ID':<36}{'Status':<30}{'Created':<20}")
        for activity in results["results"]:
            created_time_isoformatted = activity["created_time"]
            created_time = time.strftime("%Y-%m-%d %H:%M", time.strptime(created_time_isoformatted, "%Y-%m-%dT%H:%M:%S.%fZ"))
            print(
                f"{activity['id'] or '*null*':<36}{activity['workflow_status__name'] or '*null*':<30}{created_time:<20}"
            )
            for doc in activity["documents"]:
                print(f"  {doc['filename']:<40} {doc['processing_status']:<12} {doc['url']}")
    else:
        pprint.pprint(results)


def main():
    cli()


if __name__ == "__main__":
    main()
