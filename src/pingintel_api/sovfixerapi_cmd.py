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
    type=click.Choice(["SOV", "PREM_BDX", "CLAIM_BDX", "SOV_BDX", "ACORD"], case_sensitive=False),
    default="SOV",
    help="Identify `filename` document type.  Defaults to SOV.",
)
@click.option("--callback-url", help="(Optional) Provide a URL to which results should be POSTed.", metavar="URL")
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
    "--write",
    "--no-write",
    is_flag=True,
    default=True,
    help="If set, actually write the output. Otherwise, download as a test but do not write.",
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
    delegate_to,
    noinput,
):
    if isinstance(filename, pathlib.PosixPath):
        filename = [str(filename)]

    client = get_client(ctx)
    for fn in filename:
        fix_sov_ret = client.fix_sov(
            fn,
            document_type=document_type,
            callback_url=callback_url,
            actually_write=write,
            integrations=integrations,
            output_formats=output_format,
            client_ref=client_ref,
            extra_data=extra_data,
            delegate_to=delegate_to,
            noinput=noinput,
        )
        sovid = fix_sov_ret["id"]
        local_outputs = fix_sov_ret["local_outputs"]
        click.echo(f"Executed SOV Fixer, SOVID: {sovid}")
        if local_outputs:
            for output in local_outputs:
                click.echo(f"  Wrote: {output}")


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
):
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


@cli.command()
@click.pass_context
@click.option(
    "-S",
    "--search",
    help="(Optional) Provide a search string, which can be a SOVID, a filename, an insured name, etc.",
)
@click.option(
    "-o",
    "--output-path",
    help="If specified, provide a download path for all attached files.",
)
def sov(ctx, search, output_path):
    client = get_client(ctx)
    results = client.list_activity(search=search, page_size=1)
    if not results or not results["results"]:
        logger.info("No results found.")
        return
    result = results["results"][0]
    output_data = result["output_data"]

    if output_path:
        for output_ret in output_data:
            client.activity_download(output_ret, actually_write=True, output_path=output_path)



@cli.command()
@click.pass_context
@click.argument("sovid_or_sudid")
@click.option(
    "-f",
    "--output-format",
    metavar="OUTPUT_FORMAT",
    help="Select an output format.",
)
@click.option(
    "--write",
    "--no-write",
    is_flag=True,
    default=True,
    help="If set, actually write the output. Otherwise, download as a test but do not write.",
)
@click.option(
    "-r",
    "--revision",
    type=int,
    default=-1,
    help='Provide a specific revision number. Defaults to the latest revision (zero "-r0" for the initial sov).',
)
@click.option(
    "--overwrite_existing",
    "--no-overwrite_existing",
    is_flag=True,
    default=False,
    help="If set, regenerate the file even if it already exists.",
)
def get_output(ctx, sovid_or_sudid, output_format, write, revision, overwrite_existing):
    client = get_client(ctx)
    output_data = client.get_or_create_output(sovid_or_sudid, output_format, revision, overwrite_existing)
    client.activity_download(output_data, actually_write=write)

def main():
    cli()


if __name__ == "__main__":
    main()
