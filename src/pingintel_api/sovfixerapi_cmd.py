#!/usr/bin/env python

# Copyright 2021-2024 Ping Data Intelligence

import json
import logging
import pathlib
import pprint
import time
from timeit import default_timer as timer
from typing import Literal

import click

from pingintel_api import SOVFixerAPIClient
from pingintel_api.api_client_base import AuthTokenNotFound
from pingintel_api.utils import set_verbosity

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
    default="prod",
)
@click.option(
    "-u",
    "--api-url",
    help="Provide base url (instead of environment, primarily for debugging)",
)
@click.option(
    "--auth-token",
    help="Provide auth token via --auth-token or SOVFIXER_AUTH_TOKEN environment variable.",
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


def get_client(ctx) -> SOVFixerAPIClient:
    environment = ctx.obj["environment"]
    auth_token = ctx.obj["auth_token"]
    api_url = ctx.obj["api_url"]
    try:
        client = SOVFixerAPIClient(environment=environment, auth_token=auth_token, api_url=api_url)
    except AuthTokenNotFound as e:
        click.echo(e)
        raise click.Abort()

    return client


def _attributes_to_dict(ctx: click.Context, attribute: click.Option, attributes: tuple[str, ...]) -> dict[str, str]:
    """Click callback that converts attributes specified in the form `key=value` to a
    dictionary. Thanks to https://stackoverflow.com/a/76601290/237091"""
    result = {}
    for arg in attributes:
        k, v = arg.split("=")
        if k in result:
            raise click.BadParameter(f"Attribute {k!r} is specified twice")
        result[k] = v

    return result


@cli.command()
@click.pass_context
@click.argument("filename", nargs=-1, required=True, type=click.Path(exists=True, dir_okay=False))
@click.option(
    "-d",
    "--document-type",
    type=click.Choice(["SOV", "PREM_BDX", "CLAIM_BDX", "SOV_BDX", "ACORD", "LOSS_RUN"], case_sensitive=False),
    default="SOV",
    help="Identify `filename` document type.  Defaults to SOV.",
)
@click.option("--callback-url", help="(Optional) Provide a URL to which results should be POSTed.", metavar="URL")
@click.option(
    "--update-callback-url",
    help="(Optional) Provide a URL to which update (SUD) results should be POSTed.",
    metavar="URL",
)
@click.option(
    "-I",
    "--integrations",
    multiple=True,
    metavar="INTEGRATION_ABBR",
    help="Request one or more integrations.",
)
@click.option(
    "-o",
    "--output-format",
    multiple=True,
    metavar="OUTPUT_FORMAT",
    help="Select one or more output formats.",
)
@click.option(
    "--client-ref", help="Arbitrary text, representing a client reference number or other identifier.", metavar="TEXT"
)
@click.option(
    "-E",
    "--extra_data",
    help="Extra data to include in the request, in the form key=value. Can be specified multiple times.",
    metavar="KEY=VALUE",
    multiple=True,
    callback=_attributes_to_dict,
)
@click.option(
    "--write/--no-write",
    is_flag=True,
    default=True,
    help="(default) Actually write the output. If disabled, download but do not persist the result to disk.",
)
@click.option(
    "-W",
    "--workflow",
    help="If set, specifies the workflow to use for processing. Defaults to the organization's default workflow.",
)
@click.option(
    "-D",
    "--delegate-to",
    metavar="ORG_SHORT_NAME",
    help="Delegate to another organization. Provide the 'short name' of the desired delegatee.  Requires the `delegate` permission.",
)
@click.option(
    "--noinput",
    is_flag=True,
    default=False,
    help="If set, do not prompt for confirmation.",
)
@click.option(
    "--no-ping-data-api",
    is_flag=True,
    default=False,
    help="If set, do not allow ping data api calls.",
)
def fix(
    ctx,
    filename,
    document_type,
    callback_url,
    integrations,
    output_format,
    client_ref,
    extra_data,
    write,
    workflow,
    delegate_to,
    noinput,
    update_callback_url,
    no_ping_data_api,
):
    """Extract insurance information from file(s).  The filename argument is required and can be specified multiple times."""
    if isinstance(filename, pathlib.Path):
        filenames = [str(filename)]
    else:
        filenames = filename

    client = get_client(ctx)
    # for fn in filename:
    fix_sov_ret = client.fix_sov(
        filenames,
        document_type=document_type,
        callback_url=callback_url,
        actually_write=write,
        integrations=integrations,
        output_formats=output_format,
        client_ref=client_ref,
        extra_data=extra_data,
        delegate_to=delegate_to,
        noinput=noinput,
        update_callback_url=update_callback_url,
        allow_ping_data_api=not no_ping_data_api,
        workflow=workflow,
    )
    sovid = fix_sov_ret["id"]
    local_outputs = fix_sov_ret["local_outputs"]
    click.echo(f"Executed SOV Fixer, SOVID: {sovid}")
    if local_outputs:
        for output in local_outputs:
            click.echo(f"  Wrote: {output}")


@cli.command()
@click.pass_context
@click.argument("sovid")
def check_progress(ctx, sovid):
    """Check the progress of a submission."""
    client = get_client(ctx)
    response = client.fix_sov_async_check_progress(sovid)
    pprint.pprint(response)


@cli.command()
@click.pass_context
@click.option("--id", "--sovid", help="SOV ID to retrieve")
@click.option("--cursor-id", help="Cursor ID to start from")
@click.option("--prev-cursor-id")
@click.option("-l", "--page-size", "--limit", default=50)
@click.option("--fields", multiple=True)
@click.option("--search", help="Filter key fields by an arbitrary string")
@click.option("--origin", type=click.Choice(["api", "email"]))
@click.option("--status", type=click.Choice(["P", "I", "E", "R", "C", "F"]))
@click.option("--organization__short_name")
@click.option(
    "-D",
    "--download",
    metavar="OUTPUT_PATH",
    help="Download all attached files to OUTPUT_PATH",
    type=click.Path(exists=False, dir_okay=True, file_okay=False, resolve_path=True, path_type=pathlib.Path),
)
def activity(
    ctx,
    id=None,
    cursor_id=None,
    prev_cursor_id=None,
    page_size=50,
    fields: list[str] | None = None,
    search=None,
    origin: Literal["api", "email"] | None = None,
    status: Literal["P", "I", "E", "R", "C", "F"] | None = None,
    organization__short_name=None,
    download=None,
):
    """List submission activity."""
    client = get_client(ctx)
    results = client.list_activity(
        id=id,
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

    if download:
        for result in results["results"]:
            input_data = result["input_data"]
            for input_ret in input_data:
                output_path = download / input_ret["filename"]
                client.activity_download(input_ret, actually_write=True, output_path=output_path)
                click.echo(f"Downloaded: {output_path}")
            output_data = result["output_data"]
            for output_ret in output_data:
                output_path = download / output_ret["scrubbed_filename"]
                client.activity_download(output_ret, actually_write=True, output_path=output_path)
                click.echo(f"Downloaded: {output_path}")
            updates = result["updates"]
            for rev, update_ret in updates.items():
                update_outputs = update_ret["outputs"]
                for update_output in update_outputs:
                    filename = update_output["url"].split("/")[-1]
                    output_path = download / f"r{int(rev):0000d}-{filename}"
                    client.activity_download(update_output, actually_write=True, output_path=output_path)
                    click.echo(f"Downloaded: {output_path}")


@cli.command()
@click.pass_context
@click.argument("sovid_or_sudid")
@click.option(
    "-o",
    "--output-format",
    metavar="OUTPUT_FORMAT",
    help="Select an output format.",
)
@click.option(
    "--write/--no-write",
    is_flag=True,
    default=True,
    help="(default) Actually write the output. If disabled, download but do not persist the result to disk.",
)
@click.option(
    "-r",
    "--revision",
    type=int,
    default=-1,
    help='Provide a specific revision number. Defaults to the latest revision (zero "-r0" for the initial sov).',
)
@click.option(
    "--overwrite-existing/--no-overwrite-existing",
    is_flag=True,
    default=False,
    help="If set, regenerate the file even if it already exists.",
)
def get_output(ctx, sovid_or_sudid, output_format, write, revision, overwrite_existing):
    """Fetch or generate an output from a previous extraction."""
    client = get_client(ctx)
    output_data = client.get_or_create_output(sovid_or_sudid, output_format, revision, overwrite_existing)
    ret = client.activity_download(output_data, actually_write=write)
    click.echo(f"Downloaded: {ret}")


# Removed temporarily, incomplete without update bldg, remove bldg, etc.
# @cli.command()
# @click.pass_context
# @click.argument("sovid")
# @click.argument("building_data_path", type=click.Path(exists=True))
# def add_building(ctx, sovid, building_data_path):
#     """Adds a building as an annotation to an existing SOV."""

#     client = get_client(ctx)
#     with open(building_data_path, "r") as file:
#         data = json.load(file)
#     response = client.add_building(sovid, data)
#     pprint.pprint(response)


def main():
    cli()


if __name__ == "__main__":
    main()
