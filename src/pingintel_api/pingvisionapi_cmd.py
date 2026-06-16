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
    "--delegate-to-company",
    help="Delegate to another organization. Provide the company uuid, short_name, or id of the desired delegatee team.  Requires the `delegate` permission. If set but `delegate_to_team` is not set, the API will return an error if the company has multiple teams.",
)
@click.option(
    "--delegate-to",
    "--delegate-to-team",
    metavar="TEAM_UUID",
    help="Delegate to another organization. Provide the 'uuid' of the desired delegatee team.  Requires the `delegate` permission. If set, `delegate_to_company` is required. Can be team uuid, or id",
)
def create(ctx, filename, poll_until_ready, team, insured_name, delegate_to_company, delegate_to):
    """Create new submission from file(s)."""

    if isinstance(filename, pathlib.PosixPath):
        filename = [str(filename)]

    client = get_client(ctx)
    ret = client.create_submission(
        filepaths=filename,
        delegate_to_team=delegate_to,
        delegate_to_company=delegate_to_company,
        insured_name=insured_name,
        team_uuid=team,
    )
    pingid = ret["id"]
    url = ret["url"]

    print(f"Submission created: {pingid}")
    print(url)

    if poll_until_ready:
        while True:
            ret = client.list_submission_activity(pingid=pingid)
            ret = ret["results"][0] if ret["results"] else {}
            pprint.pprint(ret)
            if ret["workflow_status_name"] == "Completed":
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
@click.option("--pretty", is_flag=True, default=False)
@click.option("--include-statuses", is_flag=True, default=False, help="Include status names and UUIDs in pretty output")
@click.option("-f", "--filter", "filter_str", help="Filter teams by name or company (case-insensitive substring match)")
@click.option(
    "--delegate-to-company",
    help="Delegate to another organization. Provide the company uuid, short_name, or id of the desired delegatee team.  Requires the `delegate` permission. If set but `delegate_to_team` is not set, the API will return an error if the company has multiple teams.",
)
@click.option(
    "--delegate-to",
    "--delegate-to-team",
    metavar="TEAM_UUID",
    help="Delegate to another organization. Provide the 'uuid' of the desired delegatee team.  Requires the `delegate` permission. If set, `delegate_to_company` is required. Can be team uuid, or id",
)
@click.pass_context
def list_teams(ctx, pretty, include_statuses, filter_str, delegate_to_company, delegate_to):
    """List teams."""
    client = get_client(ctx)

    ret = client.list_teams(delegate_to_company=delegate_to_company, delegate_to_team=delegate_to)
    if not ret:
        print("No teams found.")
        return

    if filter_str:
        filter_lower = filter_str.lower()
        ret = [
            team
            for team in ret
            if filter_lower in team.get("team_name", "").lower()
            or filter_lower in team.get("company_short_name", "").lower()
        ]

    if pretty:
        print(f"{'Company':<50}{'Division':<60}{'Team':<60}")
        for team in ret:
            company = f"{team['company_short_name']} ({team['company_uuid']})"
            division = team["division_name"] + f" ({team['division_uuid']})"
            team_name = team["team_name"] + f" ({team['team_uuid']})"
            print(f"{company:<50}{division:<60}{team_name:<60}")

            if include_statuses:
                statuses = team.get("statuses", [])
                print("  Statuses:")
                for status in statuses:
                    print(f"    {status.get('name', ''):<30}{status.get('uuid', ''):<36}")
    else:
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
@click.option(
    "--sort-order",
    type=click.Choice(["asc", "desc"], case_sensitive=False),
    default="desc",
    show_default=True,
)
# @click.option("--organization__short_name")
def activity(ctx, pretty, id, cursor_id, prev_cursor_id, page_size, fields, search, sort_order):
    """List submission activity."""
    client = get_client(ctx)

    results = client.list_submission_activity(
        page_size=page_size,
        pingid=id,
        cursor_id=cursor_id,
        prev_cursor_id=prev_cursor_id,
        fields=fields,
        search=search,
        sort_order=sort_order,
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
@click.argument("pingid")
@click.option(
    "-o",
    "--output-format",
    required=True,
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
    "--overwrite-existing/--no-overwrite-existing",
    is_flag=True,
    default=False,
    help="If set, regenerate the file even if it already exists.",
)
def get_output(ctx, pingid, output_format, write, overwrite_existing):
    """Fetch or generate an output from a previous submission."""
    client = get_client(ctx)
    output_data = client.get_or_create_output(
        pingid,
        output_format,
        overwrite_existing,
    )
    output_url = output_data["url"]
    filename = output_data.get("scrubbed_filename") or pathlib.Path(output_url).name
    if write:
        client.download_document(filename, document_url=output_url)
        click.echo(f"Downloaded: {filename}")
    else:
        click.echo(output_url)


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


@cli.command()
@click.pass_context
@click.option("--pretty", is_flag=True, default=False)
@click.option("--pingid", help="Filter by Ping ID")
@click.option("--division", help="Filter by division UUID or short name")
@click.option("--team", help="Filter by team UUID or short name")
@click.option("--start", help="Start datetime filter (YYYYMMDDHHmmss UTC)")
@click.option("--cursor-id", help="Cursor ID for pagination")
@click.option("-l", "--page-size", "--limit", default=50)
def events(ctx, pretty, pingid, division, team, start, cursor_id, page_size):
    """List submission events."""
    import datetime

    client = get_client(ctx)

    if not any([pingid, division, team]):
        raise click.UsageError("One or more of --pingid, --division, or --team must be provided.")

    start_dt = None
    if start:
        start_dt = datetime.datetime.strptime(start, "%Y%m%d%H%M%S")

    results = client.list_submission_events(
        pingid=pingid,
        division=division,
        team=team,
        start=start_dt,
        cursor_id=cursor_id,
        page_size=page_size,
    )
    if pretty:
        print(f"{'Ping ID':<20}{'Event Type':<6}{'Created':<20}{'Message'}")
        for event in results["results"]:
            created = event["created_time"]
            try:
                created = time.strftime("%Y-%m-%d %H:%M", time.strptime(created, "%Y-%m-%dT%H:%M:%S.%fZ"))
            except ValueError:
                pass
            print(f"{event['pingid']:<20}{event['event_type']:<6}{created:<20}{event.get('message', '')}")
        cursor = results.get("cursor_id")
        if cursor:
            print(f"\nNext cursor: {cursor}")
    else:
        pprint.pprint(results)


# ---------------------------------------------------------------------------
# Policy Term Layer Structure APIs
# ---------------------------------------------------------------------------

@cli.command()
@click.pass_context
@click.option("--pingid", required=True, help="Ping ID of the submission.")
@click.option("--layer-structure-uuid", required=True, help="UUID of the layer structure to duplicate.")
@click.option("--name", default=None, help="Name for the duplicate. Defaults to the source name.")
def duplicate_layer_structure(ctx, pingid, layer_structure_uuid, name):
    """Duplicate a layer structure, copying all of its layers.

    pingvisionapi duplicate-layer-structure --pingid <pingid> --layer-structure-uuid <uuid> [--name <name>]
    """

    client = get_client(ctx)

    results = client.duplicate_layer_structure(
        pingid=pingid,
        layer_structure_uuid=layer_structure_uuid,
        name=name,
    )

    pprint.pprint(results)


@cli.command()
@click.pass_context
@click.option("--pingid", required=True, help="Ping ID of the submission.")
def list_layer_structures(ctx, pingid):
    """List all layer structures for a submission.

    pingvisionapi list-layer-structures --pingid <pingid>
    """

    client = get_client(ctx)

    results = client.list_layer_structures(pingid=pingid)

    pprint.pprint(results)


@cli.command()
@click.pass_context
@click.option("--pingid", required=True, help="Ping ID of the submission.")
@click.option("--name", default=None, help="Layer structure name. Auto-generated if omitted.")
def create_layer_structure(ctx, pingid, name):
    """Create a layer structure for a submission.

    pingvisionapi create-layer-structure --pingid <pingid> [--name <name>]
    """

    client = get_client(ctx)

    results = client.create_layer_structure(pingid=pingid, name=name)

    pprint.pprint(results)


@cli.command()
@click.pass_context
@click.option("--pingid", required=True, help="Ping ID of the submission.")
@click.option("--layer-structure-uuid", required=True, help="UUID of the layer structure.")
@click.option("--name", default=None, help="Layer name. Auto-generated from limit/attachment if omitted.")
@click.option("--included/--not-included", default=None, help="Whether the layer is included.")
@click.option("--attachment", type=float, default=None, help="Attachment point.")
@click.option("--limit", type=float, default=None, help="Layer limit.")
@click.option("--participation-amount", type=float, default=None, help="Participation as a currency amount.")
@click.option("--participation-percent", type=float, default=None, help="Participation as a percentage.")
@click.option("--premium", type=float, default=None, help="Layer premium.")
def add_layer_to_layer_structure(ctx, pingid, layer_structure_uuid, name, included, attachment, limit, participation_amount, participation_percent, premium):
    """Add a layer to a layer structure.

    pingvisionapi add-layer-to-layer-structure --pingid <pingid> --layer-structure-uuid <uuid> [--name <name>] [--attachment <amount>] [--limit <amount>]
    """

    client = get_client(ctx)

    results = client.add_layer_to_layer_structure(
        pingid=pingid,
        layer_structure_uuid=layer_structure_uuid,
        name=name,
        included=included,
        attachment=attachment,
        limit=limit,
        participation_amount=participation_amount,
        participation_percent=participation_percent,
        premium=premium,
    )

    pprint.pprint(results)


# ---------------------------------------------------------------------------
# Policy Term Coverage Option APIs
# ---------------------------------------------------------------------------

@cli.command()
@click.pass_context
@click.option("--pingid", required=True, help="Ping ID of the submission.")
@click.option("--coverage-option-uuid", required=True, help="UUID of the coverage option to duplicate.")
@click.option("--name", default=None, help="Name for the duplicate. Defaults to the source name.")
def duplicate_coverage_option(ctx, pingid, coverage_option_uuid, name):
    """Duplicate a coverage option, copying all of its peril and zone terms.

    pingvisionapi duplicate-coverage-option --pingid <pingid> --coverage-option-uuid <uuid> [--name <name>]
    """

    client = get_client(ctx)

    results = client.duplicate_coverage_option(
        pingid=pingid,
        coverage_option_uuid=coverage_option_uuid,
        name=name,
    )

    pprint.pprint(results)


@cli.command()
@click.pass_context
@click.option("--pingid", required=True, help="Ping ID of the submission.")
def list_coverage_options(ctx, pingid):
    """List all coverage options for a submission.

    pingvisionapi list-coverage-options --pingid <pingid>
    """

    client = get_client(ctx)

    results = client.list_coverage_options(pingid=pingid)

    pprint.pprint(results)


@cli.command()
@click.pass_context
@click.option("--pingid", required=True, help="Ping ID of the submission.")
@click.option("--name", default=None, help="Coverage option name. Defaults to 'Coverage Option' if omitted.")
def create_coverage_option(ctx, pingid, name):
    """Create a coverage option for a submission.

    pingvisionapi create-coverage-option --pingid <pingid> [--name <name>]
    """

    client = get_client(ctx)

    results = client.create_coverage_option(pingid=pingid, name=name)

    pprint.pprint(results)


# ---------------------------------------------------------------------------
# Policy Term Acc/Loc Job APIs
# ---------------------------------------------------------------------------

@cli.command()
@click.pass_context
@click.option("--pingid", help="Filter by Ping ID")
@click.option("--modeling-option-uuids", multiple=True, help="Filter by modeling option UUIDs")
@click.option("--cat-model-type", help="AIR/RMS")
@click.option("--use-secondary-modifiers", type=bool, help="Use secondary modifiers (True/False)")
@click.option("--use-ping-geocoding", type=bool, help="Use Ping geocoding (True/False)")
@click.option("--layer-output", help="Layer output")
@click.option("--air-modeling-workflow-name", help="AIR modeling workflow name")
@click.option("--rms-edm-name", help="RMS EDM name")
def create_acc_loc_job(ctx, pingid, modeling_option_uuids, cat_model_type, use_secondary_modifiers, use_ping_geocoding, layer_output, air_modeling_workflow_name, rms_edm_name):
    """Create an ACC LOC file generation job.

    pingvisionapi create-acc-loc-job --pingid <pingid> [--modeling-option-uuids <uuid1> --modeling-option-uuids <uuid2> ...] [--cat-model-type <AIR/RMS>] [--use-secondary-modifiers True/False] [--use-ping-geocoding True/False] [--layer-output <layer_output>] [--air-modeling-workflow-name <workflow_name>] [--rms-edm-name <edm_name>]
    """

    client = get_client(ctx)

    if not pingid:
        raise click.UsageError("The --pingid option is required.")

    results = client.create_acc_loc_job(
        pingid=pingid,
        modeling_option_uuids=modeling_option_uuids,
        cat_model_type=cat_model_type,
        use_secondary_modifiers=use_secondary_modifiers,
        use_ping_geocoding=use_ping_geocoding,
        layer_output=layer_output,
        air_modeling_workflow_name=air_modeling_workflow_name,
        rms_edm_name=rms_edm_name,
    )

    pprint.pprint(results)


@cli.command()
@click.pass_context
@click.option("--pingid", required=True, help="Ping ID of the submission.")
@click.option("--job-uuid", required=True, help="UUID of the acc/loc file generation job.")
def get_acc_loc_job(ctx, pingid, job_uuid):
    """Get the status of an ACC LOC file generation job.

    pingvisionapi get-acc-loc-job --pingid <pingid> --job-uuid <job_uuid>
    """

    client = get_client(ctx)

    results = client.get_acc_loc_job(
        pingid=pingid,
        job_uuid=job_uuid,
    )

    pprint.pprint(results)


# ---------------------------------------------------------------------------
# Policy Term Modeling Option APIs
# ---------------------------------------------------------------------------

@cli.command()
@click.pass_context
@click.option("--pingid", required=True, help="Ping ID of the submission.")
@click.option("--layer-structure-uuid", required=True, help="UUID of the layer structure.")
@click.option("--coverage-option-uuids", multiple=True, required=True, help="Coverage option UUID(s) to add.")
def add_modeling_options_all_layers(ctx, pingid, layer_structure_uuid, coverage_option_uuids):
    """Associate coverage options with every layer in a layer structure.

    pingvisionapi add-modeling-options-all-layers --pingid <pingid> --layer-structure-uuid <uuid> --coverage-option-uuids <uuid1> --coverage-option-uuids <uuid2>
    """

    client = get_client(ctx)

    results = client.add_modeling_options_all_layers(
        pingid=pingid,
        layer_structure_uuid=layer_structure_uuid,
        coverage_option_uuids=list(coverage_option_uuids),
    )

    pprint.pprint(results)


@cli.command()
@click.pass_context
@click.option("--pingid", required=True, help="Ping ID of the submission.")
@click.option("--layer-structure-uuid", required=True, help="UUID of the layer structure.")
@click.option("--coverage-option-uuids", multiple=True, required=True, help="Coverage option UUID(s) to remove.")
def remove_modeling_options_all_layers(ctx, pingid, layer_structure_uuid, coverage_option_uuids):
    """Remove coverage options from every layer in a layer structure.

    pingvisionapi remove-modeling-options-all-layers --pingid <pingid> --layer-structure-uuid <uuid> --coverage-option-uuids <uuid1> --coverage-option-uuids <uuid2>
    """

    client = get_client(ctx)

    results = client.remove_modeling_options_all_layers(
        pingid=pingid,
        layer_structure_uuid=layer_structure_uuid,
        coverage_option_uuids=list(coverage_option_uuids),
    )

    pprint.pprint(results)


@cli.command()
@click.pass_context
@click.option("--pingid", required=True, help="Ping ID of the submission.")
def export_modeling_options(ctx, pingid):
    """Export all modeling options for a submission.

    pingvisionapi export-modeling-options --pingid <pingid>
    """

    client = get_client(ctx)

    results = client.export_modeling_options(pingid=pingid)

    pprint.pprint(results)


def main():
    cli()


if __name__ == "__main__":
    main()
