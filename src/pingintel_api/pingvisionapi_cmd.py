#!/usr/bin/env python

# Copyright 2021-2024 Ping Data Intelligence

import logging
import pathlib
import pprint
import time
from timeit import default_timer as timer

import click

from pingintel_api import PingVisionAPIClient
from pingintel_api.api_client_base import AuthTokenNotFound
from pingintel_api.utils import set_verbosity

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
    "-u",
    "--api-url",
    help="Provide base url (instead of environment, primarily for debugging)",
)
@click.option(
    "--auth-token",
    help="Provide auth token via --auth-token or PINGVISION_AUTH_TOKEN environment variable.",
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


def get_client(ctx) -> PingVisionAPIClient:
    environment = ctx.obj["environment"]
    auth_token = ctx.obj["auth_token"]
    api_url = ctx.obj["api_url"]
    try:
        client = PingVisionAPIClient(environment=environment, auth_token=auth_token, api_url=api_url)
    except AuthTokenNotFound as e:
        click.echo(e)
        raise click.Abort()

    return client


@cli.command()
@click.pass_context
@click.argument("filename", nargs=-1, required=True, type=click.Path(exists=True, dir_okay=False))
# @click.option("--client-ref")
@click.option(
    "--poll-until-ready",
    is_flag=True,
    default=False,
    help="If set, poll until the submission is ready.",
)
@click.option("--insured-name")
@click.option(
    "--team",
    "--team-uuid",
    help="Team UUID to use for the submission. Optional unless you can access more than one team.",
)
@click.option(
    "--delegate-to",
    "--delegate-to-team",
    metavar="TEAM_UUID",
    help="Delegate to another organization. Provide the 'uuid' of the desired delegatee team.  Requires the `delegate` permission.",
)
def create(ctx, filename, poll_until_ready, team, insured_name, delegate_to):
    """Create new submission from file(s)."""

    if isinstance(filename, pathlib.PosixPath):
        filename = [str(filename)]

    client = get_client(ctx)
    ret = client.create_submission(
        filepaths=filename, delegate_to_team=delegate_to, insured_name=insured_name, team_uuid=team
    )
    pingid = ret["id"]
    url = ret["url"]

    print(f"Submission created: {pingid}")
    print(url)

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
    """Get submission detail."""
    client = get_client(ctx)

    ret = client.get_submission_detail(pingid=pingid)
    pprint.pprint(ret)


@cli.command()
@click.pass_context
def list_teams(ctx):
    """List teams."""
    client = get_client(ctx)

    ret = client.list_teams()
    if not ret:
        print("No teams found.")
        return

    print(f"{'Team Name':<40}{'UUID':<36}")
    for team in ret:
        print(f"{team['team_name']:<40}{team['team_uuid']:<36}")


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
    """List submission activity."""
    client = get_client(ctx)

    results = client.list_submission_activity(
        page_size=page_size,
        pingid=id,
        cursor_id=cursor_id,
        prev_cursor_id=prev_cursor_id,
        fields=fields,
        search=search,
    )
    if pretty:
        print(f"{'Activity ID':<36}{'Status':<30}{'Created':<20}")
        for activity in results["results"]:
            created_time_isoformatted = activity["created_time"]
            created_time = time.strftime(
                "%Y-%m-%d %H:%M",
                time.strptime(created_time_isoformatted, "%Y-%m-%dT%H:%M:%S.%fZ"),
            )
            print(
                f"{activity['id'] or '*null*':<36}{activity['workflow_status_name'] or '*null*':<30}{created_time:<20}"
            )
            for doc in activity["documents"]:
                print(f"  {doc['filename']:<40} {doc['url']}")
    else:
        pprint.pprint(results)


@cli.command()
@click.pass_context
@click.argument("document_url")
@click.option("-o", "--output", type=click.File("wb"))
def download_document(ctx, document_url, output):
    """Download document by document URL."""
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


@cli.command()
@click.pass_context
@click.option("-d", "--division", type=str, help="Division UUID to filter by")
def list_submission_statuses(ctx, division):
    """List submission statuses."""
    client = get_client(ctx)

    results = client.list_submission_statuses(division=division)
    if not results:
        print("No submission statuses found.")
        return
    pprint.pprint(results)


def main():
    cli()


if __name__ == "__main__":
    main()
