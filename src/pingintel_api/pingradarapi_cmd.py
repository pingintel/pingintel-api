#!/usr/bin/env python

# Copyright 2021-2024 Ping Data Intelligence

import logging
import pathlib
import pprint
import time
from timeit import default_timer as timer

import click

from pingintel_api import PingRadarAPIClient

logger = logging.getLogger(__name__)


global start_time
start_time = None


"""
pingradarapi.py

Example Python commandline script for using the Ping Data Technologies Ping Radar API to process SOVs.
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
    help="Provide auth token via --auth-token or PINGRADAR_AUTH_TOKEN environment variable.",
)
@click.pass_context
def cli(ctx, environment, api_url, auth_token):
    ctx.ensure_object(dict)
    ctx.obj["environment"] = environment
    ctx.obj["auth_token"] = auth_token
    ctx.obj["api_url"] = api_url


def get_client(ctx) -> PingRadarAPIClient:
    environment = ctx.obj["environment"]
    auth_token = ctx.obj["auth_token"]
    api_url = ctx.obj["api_url"]
    client = PingRadarAPIClient(
        environment=environment, auth_token=auth_token, api_url=api_url
    )
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
@click.option("--id", "--sovid", help="SOV ID to retrieve")
@click.option("--cursor-id", help="Cursor ID to start from")
@click.option("--prev-cursor-id")
@click.option("-l", "--page-size", "--limit", default=50)
@click.option("--fields", multiple=True)
@click.option("--search", help="Filter key fields by an arbitrary string")
# @click.option("--organization__short_name")
def activity(ctx, pretty, id, cursor_id, prev_cursor_id, page_size, fields, search):
    client = get_client(ctx)

    results = client.list_submission_activity(
        page_size=page_size,
        id=id,
        cursor_id=cursor_id,
        prev_cursor_id=prev_cursor_id,
        fields=fields,
        search=search,
    )
    if pretty:
        """print it like a table"""
        print(f"{'Activity ID':<36}{'Status':<30}{'Created':<20}")
        for activity in results["results"]:
            created_time_isoformatted = activity["created_time"]
            created_time = time.strftime(
                "%Y-%m-%d %H:%M",
                time.strptime(created_time_isoformatted, "%Y-%m-%dT%H:%M:%S.%fZ"),
            )
            print(
                f"{activity['id'] or '*null*':<36}{activity['workflow_status__name'] or '*null*':<30}{created_time:<20}"
            )
            for doc in activity["documents"]:
                print(
                    f"  {doc['filename']:<40} {doc['processing_status']:<12} {doc['url']}"
                )
    else:
        pprint.pprint(results)


@cli.command()
@click.pass_context
@click.argument("document_url")
@click.option("-o", "--output", type=click.File("wb"))
def download_document(ctx, document_url, output):
    if not output:
        import urllib.parse, os

        output = pathlib.Path(document_url).name
        output = urllib.parse.unquote(output)
        if os.path.exists(output):
            confirm = input(f"File {output} already exists. Overwrite? (y/n) ")
            if confirm.lower() != "y":
                print("Exiting.")
                return
        output = open(output, "wb")
    client = get_client(ctx)

    results = client.download_document(output, document_url)

    print(f"Downloaded file to {output.name}")


def main():
    cli()


if __name__ == "__main__":
    main()
