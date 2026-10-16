#!/usr/bin/env python

# Copyright 2021-2024 Ping Data Intelligence

from datetime import datetime
import json
import logging
import pathlib
import pprint
import re
import time
from timeit import default_timer as timer
from typing import Literal, get_args

import click

from pingintel_api import SOVFixerAPIClient
from pingintel_api.api_client_base import AuthTokenNotFound
from pingintel_api.sov_fixer.types import SOV_ANALYTICS_SUMMARY_FIELD, SOV_LOCATIONS_SORT
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
    "--delegate-to-team",
    metavar="Team UUID",
    help="Delegate to another team. Provide the 'uuid' of the desired delegatee.  Requires the `delegate` permission.",
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
@click.option(
    "--nowait",
    is_flag=True,
    default=False,
    help="If set, do not wait for the SOV Fixer to complete processing. Instead, return immediately with the SOV ID.",
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
    delegate_to_team,
    noinput,
    update_callback_url,
    no_ping_data_api,
    nowait,
):
    """Extract insurance information from file(s).  The filename argument is required and can be specified multiple times."""
    if isinstance(filename, pathlib.Path):
        filenames = [str(filename)]
    else:
        filenames = filename

    client = get_client(ctx)
    # for fn in filename:

    if nowait:
        fix_sov_ret = client.fix_sov_async_start(
            filenames,
            document_type=document_type,
            callback_url=callback_url,
            integrations=integrations,
            output_formats=output_format,
            client_ref=client_ref,
            extra_data=extra_data,
            # delegate_to=delegate_to,
            delegate_to_team=delegate_to_team,
            update_callback_url=update_callback_url,
            allow_ping_data_api=not no_ping_data_api,
            workflow=workflow,
        )
        local_outputs = None
    else:
        fix_sov_ret = client.fix_sov(
            filenames,
            document_type=document_type,
            callback_url=callback_url,
            actually_write=write,
            integrations=integrations,
            output_formats=output_format,
            client_ref=client_ref,
            extra_data=extra_data,
            # delegate_to=delegate_to,
            delegate_to_team=delegate_to_team,
            noinput=noinput,
            update_callback_url=update_callback_url,
            allow_ping_data_api=not no_ping_data_api,
            workflow=workflow,
        )
        local_outputs = fix_sov_ret["local_outputs"]

    sovid = fix_sov_ret["id"]
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
def serverinfo(ctx):
    client = get_client(ctx)
    response = client.get(client.api_url + "/api/v1/serverinfo")
    pprint.pprint(response.json())


@cli.command()
@click.pass_context
@click.option("--cursor-id", help="Cursor ID to start from")
@click.option("-l", "--page-size", "--limit", default=50)
@click.option(
    "--start",
    type=click.DateTime(formats=["%Y-%m-%d", "%Y-%m-%d %H:%M:%S"]),
    help="Start datetime to filter results from (e.g., '2024-06-01' or '2024-06-01 13:00:00')",
)
@click.option("--pretty", is_flag=True, default=False)
def history(
    ctx,
    cursor_id=None,
    page_size=50,
    start: datetime | None = None,
    pretty=False,
):
    """List submission activity."""
    client = get_client(ctx)
    results = client.list_history(
        cursor_id=cursor_id,
        page_size=page_size,
        start=start,
    )

    for activity in results["results"]:
        if pretty:
            print(
                f"{activity['pingid']}/{activity['id']}: {activity['record_type']} {activity['completed_time'].strftime('%Y-%m-%d %H:%M:%S')} Status: {activity['status']}"
            )
        else:
            pprint.pprint(activity)


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
@click.option("--company__short_name", multiple=True)
@click.option("--division__short_name", multiple=True)
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
    company__short_name: tuple[str, ...] = (),
    division__short_name: tuple[str, ...] = (),
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
        company__short_name=list(company__short_name) or None,
        division__short_name=list(division__short_name) or None,
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
@click.option(
    "-D",
    "--delegate-to-team",
    metavar="Team UUID",
    help="Delegate to another team. Provide the 'uuid' of the desired delegatee.  Requires the `delegate` permission.",
)
def get_output(ctx, sovid_or_sudid, output_format, write, revision, overwrite_existing, delegate_to_team):
    """Fetch or generate an output from a previous extraction."""
    client = get_client(ctx)
    click.echo(f"Requesting {output_format} output for {sovid_or_sudid}...")

    def show_progress(response_data):
        request = response_data.get("request", {})
        status = request.get("status")
        pct = request.get("pct_complete")
        pct_str = f", {pct}% complete" if pct is not None else ""
        click.echo(f"  - {status}{pct_str}...")

    try:
        output_data = client.get_or_create_output(
            sovid_or_sudid,
            output_format,
            revision,
            overwrite_existing,
            delegate_to_team=delegate_to_team,
            on_progress=show_progress,
        )
        filename = output_data.get("scrubbed_filename") or output_format
        click.echo(f"Output ready, downloading {filename}...")
        ret = client.activity_download(output_data, actually_write=write)
    except (RuntimeError, ValueError, TimeoutError) as e:
        raise click.ClickException(str(e))
    if write:
        if ret is None:
            raise click.ClickException(f"Download of {filename} failed; see warning above for details.")
        click.echo(f"Downloaded: {ret}")
    else:
        click.echo("Download complete (not written to disk; --no-write).")


@cli.command()
@click.pass_context
@click.argument("sovid")
@click.argument(
    "location_filename",
    nargs=-1,
    required=True,
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "-o",
    "--output-format",
    multiple=True,
    metavar="OUTPUT_FORMAT",
    help="Select one or more output formats.",
)
@click.option(
    "-I",
    "--integrations",
    multiple=True,
    metavar="INTEGRATION_ABBR",
    help="Request one or more integrations.",
)
@click.option(
    "--callback-url",
    help="(Optional) Provide a URL to which results should be POSTed.",
    metavar="URL",
)
@click.option(
    "--update-type",
    help="(Optional) Specify the update type.",
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
    "-D",
    "--delegate-to-team",
    metavar="Team UUID",
    help="Delegate to another team. Provide the 'uuid' of the desired delegatee.  Requires the `delegate` permission.",
)
@click.option(
    "--noinput",
    is_flag=True,
    default=False,
    help="If set, do not prompt for confirmation.",
)
@click.option(
    "--nowait",
    is_flag=True,
    default=False,
    help="If set, do not wait for the update to complete. Instead, return immediately with the SUD ID.",
)
def update(
    ctx,
    sovid,
    location_filename,
    output_format,
    integrations,
    callback_url,
    update_type,
    extra_data,
    write,
    delegate_to_team,
    noinput,
    nowait,
):
    """Update an existing SOV with new location data."""
    client = get_client(ctx)
    sudid = client.update_sov(
        sovid,
        location_filenames=location_filename,
        output_formats=output_format if output_format else None,
        integrations=integrations if integrations else None,
        callback_url=callback_url,
        update_type=update_type,
        extra_data=extra_data if extra_data else None,
        actually_write=write,
        delegate_to_team=delegate_to_team,
        noinput=noinput,
        wait_for_completion=not nowait,
    )
    click.echo(f"Executed SOV Update, SUDID: {sudid}")


@cli.command()
@click.pass_context
@click.option("--sovid", help="Scope to a specific SOV ID")
@click.option("--division-uuid", help="Scope to a division UUID")
@click.option("--team-uuid", help="Scope to a team UUID")
@click.option("--pretty", is_flag=True, default=False)
def list_output_formats(ctx, sovid, division_uuid, team_uuid, pretty):
    """List available output formats."""
    client = get_client(ctx)
    results = client.list_output_formats(sovid=sovid, division_uuid=division_uuid, team_uuid=team_uuid)
    if pretty:
        print(f"{'Format':<30}{'Label':<40}{'Extension':<12}{'Public'}")
        for fmt in results["output_formats"]:
            ext = fmt.get("output_extension") or ""
            print(f"{fmt['output_format']:<30}{fmt['label']:<40}{ext:<12}{fmt['is_public']}")
    else:
        pprint.pprint(results)


_FILTER_RE = re.compile(r"^(?P<field>[^\[\]=]+)(?:\[(?P<op>[^\[\]=]+)\])?=(?P<value>.*)$")


def _filters_to_dict(ctx: click.Context, param: click.Parameter, values: tuple[str, ...]) -> dict:
    """Click callback: `-f state=TX -f state=FL -f 'const__bldg_year_built[gte]=1990'` becomes
    `{"state": ["TX", "FL"], "const__bldg_year_built": {"gte": ["1990"]}}`."""
    filters: dict = {}
    for arg in values:
        m = _FILTER_RE.match(arg)
        if not m:
            raise click.BadParameter(f"Expected FIELD=VALUE or FIELD[op]=VALUE, got {arg!r}")
        field, op, value = m["field"], m["op"], m["value"]
        if op is None:
            exact = filters.setdefault(field, [])
            if not isinstance(exact, list):
                raise click.BadParameter(f"Filter {field!r} mixes exact values with operators: {arg!r}")
            exact.append(value)
        else:
            ops = filters.setdefault(field, {})
            if not isinstance(ops, dict):
                raise click.BadParameter(f"Filter {field!r} mixes exact values with operators: {arg!r}")
            ops.setdefault(op, []).append(value)
    return filters


def _analytics_options(f):
    """Options shared by the SOV analytics commands. Applied bottom-up, so they list in this order."""
    f = click.option("--pretty", is_flag=True, default=False, help="Print a short table instead of JSON.")(f)
    f = click.option(
        "-f",
        "--filter",
        "filters",
        multiple=True,
        metavar="FIELD[op]=VALUE",
        callback=_filters_to_dict,
        help="Location filter, e.g. -f state=TX -f state=FL -f 'const__bldg_year_built[gte]=1990'. Repeat a field to "
        "match any of its values. Operators: gt, gte, lt, lte, gt_or_null, gte_or_null, lt_or_null, lte_or_null, not_in, bins.",
    )(f)
    f = click.argument("id")(f)
    return f


def _layer_options(f):
    f = click.option("--layer-limit", type=int, help="Layer limit for limits__total_limit_in_layer.")(f)
    f = click.option("--layer-attach", type=int, help="Layer attachment point for limits__total_limit_in_layer.")(f)
    return f


def _echo_json(result):
    click.echo(json.dumps(result, indent=2))


def _fmt_money(value) -> str:
    return "" if value is None else f"{value:,.0f}"


def _echo_report_rows(rows: list[dict], indent: str = "  "):
    for row in rows:
        if "limits__total_limit" in row:
            click.echo(
                f"{indent}{row['label']:<40} {row['count']:>8} {_fmt_money(row['limits__total_limit']):>18} "
                f"{row['limits__total_limit_pct']:>7.2f}%"
            )
        else:
            click.echo(
                f"{indent}{row['label']:<40} {row['count']:>8} {row['limits__building_limit_per_sqft']:>14,.2f}/sqft "
                f"{row['limits__building_limit_with_area_pct']:>7.2f}% with area"
            )


def _echo_layer_rows(rows: list[dict], indent: str = "  "):
    for row in rows:
        click.echo(
            f"{indent}{row['label']:<40} {row['count']:>8} {_fmt_money(row['limits__total_limit_in_layer']):>18} "
            f"{row['limits__total_limit_in_layer_pct']:>7.2f}%"
        )


def _echo_totals(totals: dict):
    click.echo(
        f"Locations: {totals['count']} ({totals['geocoded_count']} geocoded)  "
        f"TIV: {_fmt_money(totals['limits__total_limit'])}  "
        f"In layer: {_fmt_money(totals['limits__total_limit_in_layer'])}"
    )


@cli.command()
@click.pass_context
@_analytics_options
@_layer_options
@click.option(
    "--field",
    "fields",
    multiple=True,
    type=click.Choice(list(get_args(SOV_ANALYTICS_SUMMARY_FIELD))),
    help="Return the value distribution for this field. Can be repeated.",
)
def summary(ctx, id, filters, pretty, layer_attach, layer_limit, fields):
    """Get insured details and totals for an SOV or portfolio (pingid, sovid, or portfolio id)."""
    client = get_client(ctx)
    result = client.get_sov_summary(
        id, filters=filters, fields=fields, layer_attach=layer_attach, layer_limit=layer_limit
    )
    if not pretty:
        _echo_json(result)
        return

    click.echo(f"{result['sovid']} ({result['kind']}) {result['status']}  {result['filename'] or ''}")
    click.echo(f"Insured: {result['insured']['name']}")
    _echo_totals(result["totals"])
    for field, buckets in result["fields"].items():
        click.echo(f"\n{field}:")
        for bucket in buckets:
            click.echo(
                f"  {bucket['label']:<40} {bucket['count']:>8} {_fmt_money(bucket['limits__total_limit']):>18} "
                f"{bucket['limits__total_limit_pct']:>7.2f}%"
            )


@cli.command()
@click.pass_context
@_analytics_options
@_layer_options
@click.option("-l", "--limit", type=click.IntRange(1, 1000), help="Page size. Server default 100.")
@click.option("--offset", type=click.IntRange(0), help="Number of locations to skip.")
@click.option("--sort", type=click.Choice(list(get_args(SOV_LOCATIONS_SORT))), help="Sort order.")
@click.option("--all", "all_pages", is_flag=True, default=False, help="Follow `next` and return every location.")
def locations(ctx, id, filters, pretty, layer_attach, layer_limit, limit, offset, sort, all_pages):
    """List the locations of an SOV or portfolio that match the filters."""
    client = get_client(ctx)
    if all_pages:
        if offset is not None:
            raise click.UsageError("--offset cannot be combined with --all.")
        results = list(
            client.iter_sov_locations(
                id,
                filters=filters,
                page_size=limit or 1000,
                sort=sort,
                layer_attach=layer_attach,
                layer_limit=layer_limit,
            )
        )
        if not pretty:
            _echo_json(results)
            return
    else:
        page = client.list_sov_locations(
            id,
            filters=filters,
            limit=limit,
            offset=offset,
            sort=sort,
            layer_attach=layer_attach,
            layer_limit=layer_limit,
        )
        if not pretty:
            _echo_json(page)
            return
        results = page["results"]
        click.echo(f"{page['count']} matching locations, showing {len(results)}.")

    for loc in results:
        address = ", ".join(str(loc[k]) for k in ("street", "city", "state", "zip") if loc[k])
        click.echo(
            f"{loc['sovid']:<14} {loc['building_counter']:>6}  {_fmt_money(loc['limits__total_limit']):>16}  "
            f"{loc['const__bldg_year_built'] or '':>4}  {address}"
        )


@cli.command()
@click.pass_context
@_analytics_options
@_layer_options
@click.option("--breakdown-limit", type=click.IntRange(1, 100), help="Max rows per country/state/county breakdown.")
@click.option(
    "--exposure-analysis-min-tiv",
    "exposure_analysis_limits__total_limit__gte",
    type=click.IntRange(0),
    help="Minimum TIV of the locations counted by the exposure-analysis section rows.",
)
def exposure_report(
    ctx, id, filters, pretty, layer_attach, layer_limit, breakdown_limit, exposure_analysis_limits__total_limit__gte
):
    """Get the exposure report for an SOV or portfolio: TIV breakdowns, COPE, hazard and layer sections."""
    client = get_client(ctx)
    result = client.get_sov_exposure_report(
        id,
        filters=filters,
        breakdown_limit=breakdown_limit,
        exposure_analysis_limits__total_limit__gte=exposure_analysis_limits__total_limit__gte,
        layer_attach=layer_attach,
        layer_limit=layer_limit,
    )
    if not pretty:
        _echo_json(result)
        return

    click.echo(f"{result['sovid']} ({result['kind']})")
    _echo_totals(result["totals"])
    for group in result["breakdowns"]:
        click.echo(f"\n{group['title']}:")
        _echo_report_rows(group["rows"])
    for section in result["sections"]:
        click.echo(f"\n== {section['title']} ==")
        for group in section["groups"]:
            click.echo(f"  {group['title']}:")
            _echo_report_rows(group["rows"], indent="    ")
    click.echo(f"\nLayers ({result['layers']['tower']}):")
    _echo_layer_rows(result["layers"]["rows"])


@cli.command()
@click.pass_context
@_analytics_options
@click.option(
    "--layer",
    "layers",
    multiple=True,
    metavar="LIMITxsATTACH",
    help="Custom tower layer, e.g. --layer 5000000xs0 --layer xs5000000. Cannot be combined with --tower.",
)
@click.option("--tower", type=click.Choice(["standard"]), help="Preset tower. Server default when --layer is omitted.")
def layers(ctx, id, filters, pretty, layers, tower):
    """Get the TIV exposed to each layer of a tower, per location."""
    client = get_client(ctx)
    result = client.get_sov_layer_analysis(id, filters=filters, layers=layers, tower=tower)
    if not pretty:
        _echo_json(result)
        return

    click.echo(f"Tower: {result['tower']} ({result['basis']})")
    _echo_layer_rows(result["rows"])


def main():
    cli()


if __name__ == "__main__":
    main()
