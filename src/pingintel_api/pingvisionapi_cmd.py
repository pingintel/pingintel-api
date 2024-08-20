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
    "--auth-token",
    help="Provide auth token via --auth-token or PINGVISION_AUTH_TOKEN environment variable.",
)
@click.pass_context
def cli(ctx, environment, auth_token):
    ctx.ensure_object(dict)
    ctx.obj["environment"] = environment
    ctx.obj["auth_token"] = auth_token


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
# @click.option("--client-ref")
@click.option(
    "--poll-until-ready",
    is_flag=True,
    default=False,
    help="If set, poll until the submission is ready.",
)
def create(ctx, filename, poll_until_completion=False):
    environment = ctx.obj["environment"]
    auth_token = ctx.obj["auth_token"]

    if isinstance(filename, pathlib.PosixPath):
        filename = [str(filename)]

    client = PingVisionAPIClient(environment=environment, auth_token=auth_token)
    ret = client.create_submission(filepaths=filename)
    pingid = ret["id"]

    if poll_until_completion:
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
    environment = ctx.obj["environment"]
    auth_token = ctx.obj["auth_token"]
    client = PingVisionAPIClient(environment=environment, auth_token=auth_token)

    ret = client.get_submission_detail(pingid=pingid)
    pprint.pprint(ret)


@cli.command()
@click.pass_context
def activity(ctx):
    environment = ctx.obj["environment"]
    auth_token = ctx.obj["auth_token"]
    client = PingVisionAPIClient(environment=environment, auth_token=auth_token)
    results = client.list_submission_activity()
    pprint.pprint(results)


def main():
    cli()


if __name__ == "__main__":
    main()
