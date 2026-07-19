#!/usr/bin/env python

# Copyright 2021-2024 Ping Data Intelligence

import json
import logging
import pprint
import time
from timeit import default_timer as timer
import click

from pingintel_api import PingDataAPIClient

from pingintel_api.api_client_base import AuthTokenNotFound
from pingintel_api.pingdata.types import Location
from pingintel_api.utils import set_verbosity

logger = logging.getLogger(__name__)


global start_time
start_time = None


"""
pingdataapi.py

Example Python commandline script for using the Ping Data Technologies Data API to enhance locations with additional data.
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


def get_client(ctx) -> PingDataAPIClient:
    environment = ctx.obj["environment"]
    auth_token = ctx.obj["auth_token"]
    api_url = ctx.obj["api_url"]
    try:
        client = PingDataAPIClient(environment=environment, auth_token=auth_token, api_url=api_url)
    except AuthTokenNotFound as e:
        click.echo(e)
        raise click.Abort()

    return client


def parse_extra_kwargs(extra: tuple[str, ...]) -> dict:
    """Parse key=value pairs into a dictionary, converting numeric values."""
    result = {}
    for item in extra:
        if "=" not in item:
            raise click.BadParameter(f"Invalid format '{item}'. Expected key=value")
        key, value = item.split("=", 1)
        # Try to convert to int, then float, otherwise keep as string
        try:
            result[key] = int(value)
        except ValueError:
            try:
                result[key] = float(value)
            except ValueError:
                result[key] = value
    return result


@cli.command()
@click.pass_context
@click.option("-a", "--address", multiple=True)
@click.option(
    "-s",
    "--sources",
    multiple=True,
    required=True,
)
@click.option("-c", "--country", type=str, default=None, help="Optional. Provides a country hint to the geocoders.")
@click.option("--latitude", type=float, default=None, help="Optional. Specify latitude.")
@click.option("--longitude", type=float, default=None, help="Optional. Specify longitude.")
@click.option("--timeout", type=float, default=None, help="Optional. Maximum time to wait for response in seconds.")
@click.option("-r", "--include-raw-response", is_flag=True, help="Optional. Include raw response from all sources.")
@click.option("--nocache", is_flag=True, help="If set, do not use cache.")
@click.option(
    "-x",
    "--extra",
    multiple=True,
    metavar="KEY=VALUE",
    help="Extra location kwargs (e.g., -x const__code_rms=RC -x const__num_stories=3). Can be used multiple times.",
)
def enhance(
    ctx: click.Context,
    address: str,
    sources: list[str],
    country: str | None,
    latitude: float | None,
    longitude: float | None,
    timeout: float | None = None,
    include_raw_response: bool = False,
    nocache: bool = False,
    extra: tuple[str, ...] = (),
):
    """Request data synchronously about a single address."""

    client = get_client(ctx)

    extra_location_kwargs = parse_extra_kwargs(extra)

    response_data = client.enhance(
        address=address,
        country=country,
        latitude=latitude,
        longitude=longitude,
        sources=sources,
        timeout=timeout,
        include_raw_response=include_raw_response,
        nocache=nocache,
        delegate_to=ctx.obj["delegate_to"],
        **extra_location_kwargs,
    )
    click.echo(f"+ Finished querying with result:\n{pprint.pformat(response_data)}")


@cli.command()
@click.pass_context
@click.option("-a", "--address", multiple=True)
@click.option("-f", "--file", type=click.File("r"), help="File containing location data, one per line.")
@click.option(
    "-s",
    "--sources",
    multiple=True,
    # required=True,
)
@click.option("--timeout", type=float, default=None, help="Optional. Maximum time to wait for response in seconds.")
@click.option("-r", "--include-raw-response", is_flag=True, help="Optional. Include raw response from all sources.")
@click.option("--nocache", is_flag=True, help="If set, do not use cache.")
@click.option("--fetch-outputs/--no-fetch-outputs", is_flag=True, default=True)
@click.option("-v", "--verbose", help="Enable verbose output. Can be used up to 3 times.", count=True)
def bulk_enhance(
    ctx: click.Context,
    address: list[str],
    file: click.File,
    sources: list[str],
    timeout: float | None,
    include_raw_response: bool,
    nocache: bool,
    fetch_outputs: bool,
    verbose: int,
):
    """Request data about multiple addresses using async API."""
    client = get_client(ctx)

    locations = []
    address_id_ctr = 0
    if address:
        for addr in address:
            address_id_ctr += 1
            locations.append(Location(address=addr, id=f"id_{address_id_ctr:03d}"))

    if file:
        for line in file:
            address_id_ctr += 1
            locations.append(Location(address=line.strip(), id=f"id_{address_id_ctr:03d}"))

    response_data = client.bulk_enhance(
        locations=locations,
        sources=sources,
        timeout=timeout,
        include_raw_response=include_raw_response,
        nocache=nocache,
        fetch_outputs=fetch_outputs,
        verbose=verbose,
        delegate_to=ctx.obj["delegate_to"],
    )
    click.echo(f"+ Finished querying with result:\n{pprint.pformat(response_data)}")


@cli.command()
@click.pass_context
@click.option(
    "--start",
    type=str,
    default=None,
    help="Start of the time range. Relative offset (-5m, -1h, -30d) or ISO 8601 UTC timestamp. Defaults to -30d.",
)
@click.option(
    "--end",
    type=str,
    default=None,
    help="End of the time range. Relative offset or ISO 8601 UTC timestamp. Defaults to now.",
)
@click.option(
    "--username",
    type=str,
    default=None,
    help="Filter by username. Defaults to the requesting user. Staff only when querying another user.",
)
@click.option(
    "--org-short-name",
    type=str,
    default=None,
    help="Filter by organization short name (e.g. 'AMWNS'). Staff only. Mutually exclusive with --username.",
)
def usage(
    ctx: click.Context,
    start: str | None,
    end: str | None,
    username: str | None,
    org_short_name: str | None,
):
    """Get API credit usage over a time range, broken down by data source and time bucket."""
    client = get_client(ctx)
    response_data = client.get_usage(
        start=start,
        end=end,
        username=username,
        org_short_name=org_short_name,
        delegate_to=ctx.obj["delegate_to"],
    )
    click.echo(pprint.pformat(response_data))


@cli.command()
@click.pass_context
def list_datasources(ctx: click.Context):
    """List the datasource configurations the authenticated user has access to."""
    client = get_client(ctx)
    response_data = client.list_datasources(delegate_to=ctx.obj["delegate_to"])
    click.echo(pprint.pformat(response_data))


def _field_description(info: dict) -> str:
    """Extract the human-readable description from an output-field entry.

    Field metadata (description, display_type, etc.) is spread flat alongside `type`.
    """
    return str((info or {}).get("description", "") or "")


def _render_datasource_markdown(config: dict) -> str:
    """Render a single datasource config dict as human-readable Markdown."""
    lines: list[str] = []

    name = config.get("source_name") or config.get("source_code") or "Datasource"
    code = config.get("source_code") or ""
    lines.append(f"# {name} ({code})" if code else f"# {name}")
    lines.append("")

    conf = config.get("geocode_confidence_required")
    prec = config.get("geocode_precision_required")
    lines.append(f"- **Source code:** {code or 'None'}")
    lines.append(f"- **Requires credentials:** {'Yes' if config.get('requires_credentials') else 'No'}")
    lines.append(f"- **Geocode confidence required:** {conf if conf is not None else 'None'}")
    lines.append(f"- **Geocode precision required:** {prec if prec is not None else 'None'}")
    lines.append("")

    required = config.get("required_attrs") or []
    optional = config.get("optional_attrs") or []
    lines.append("## Input attributes")
    lines.append("")
    lines.append(f"- **Required:** {', '.join(required) if required else 'None'}")
    lines.append(f"- **Optional:** {', '.join(optional) if optional else 'None'}")
    lines.append("")

    countries = config.get("supported_countries")
    states = config.get("supported_us_states")
    excluded = config.get("excluded_us_states")
    if countries or states or excluded:
        lines.append("## Supported regions")
        lines.append("")
        if countries:
            lines.append(f"- **Countries:** {', '.join(countries)}")
        if states:
            lines.append(f"- **US states:** {', '.join(states)}")
        if excluded:
            lines.append(f"- **Excluded US states:** {', '.join(excluded)}")
        lines.append("")

    non_supported = config.get("non_supported_input_values")
    if non_supported:
        lines.append("## Non-supported input values")
        lines.append("")
        for field, values in non_supported.items():
            lines.append(f"- **{field}:** {', '.join(values) if values else 'None'}")
        lines.append("")

    def _append_field_table(title: str, fields: dict) -> None:
        if not fields:
            return
        lines.append(f"## {title}")
        lines.append("")
        lines.append("| Field | Type | Description |")
        lines.append("| --- | --- | --- |")
        for field_name, info in fields.items():
            field_type = str((info or {}).get("type", "")).replace("|", "\\|")
            description = _field_description(info).replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {field_name} | {field_type} | {description} |")
            # Nested object fields declare their sub-attributes under `fields`.
            for sub_name, sub_info in ((info or {}).get("fields") or {}).items():
                sub_type = str((sub_info or {}).get("type", "")).replace("|", "\\|")
                sub_desc = _field_description(sub_info).replace("|", "\\|").replace("\n", " ")
                lines.append(f"| {field_name}.{sub_name} | {sub_type} | {sub_desc} |")
        lines.append("")

    _append_field_table("Output fields", config.get("output_fields") or {})
    _append_field_table("Base output fields", config.get("base_output_fields") or {})

    return "\n".join(lines).rstrip() + "\n"


def _render_datasource_pretty(config: dict) -> str:
    """Render a single datasource config dict as plain readable text (no Markdown tables)."""
    lines: list[str] = []

    name = config.get("source_name") or config.get("source_code") or "Datasource"
    code = config.get("source_code") or ""
    heading = f"{name} ({code})" if code else name
    lines.append(heading)
    lines.append("=" * len(heading))
    lines.append("")

    conf = config.get("geocode_confidence_required")
    prec = config.get("geocode_precision_required")
    lines.append(f"Source code:                 {code or 'None'}")
    lines.append(f"Requires credentials:        {'Yes' if config.get('requires_credentials') else 'No'}")
    lines.append(f"Geocode confidence required: {conf if conf is not None else 'None'}")
    lines.append(f"Geocode precision required:  {prec if prec is not None else 'None'}")
    lines.append("")

    required = config.get("required_attrs") or []
    optional = config.get("optional_attrs") or []
    lines.append("Input attributes:")
    lines.append(f"  Required: {', '.join(required) if required else 'None'}")
    lines.append(f"  Optional: {', '.join(optional) if optional else 'None'}")
    lines.append("")

    countries = config.get("supported_countries")
    states = config.get("supported_us_states")
    excluded = config.get("excluded_us_states")
    if countries or states or excluded:
        lines.append("Supported regions:")
        if countries:
            lines.append(f"  Countries: {', '.join(countries)}")
        if states:
            lines.append(f"  US states: {', '.join(states)}")
        if excluded:
            lines.append(f"  Excluded US states: {', '.join(excluded)}")
        lines.append("")

    non_supported = config.get("non_supported_input_values")
    if non_supported:
        lines.append("Non-supported input values:")
        for field, values in non_supported.items():
            lines.append(f"  {field}: {', '.join(values) if values else 'None'}")
        lines.append("")

    def _append_field_section(title: str, fields: dict) -> None:
        if not fields:
            return
        lines.append(f"{title}:")
        for field_name, info in fields.items():
            field_type = str((info or {}).get("type", ""))
            lines.append(f"  {field_name} ({field_type})" if field_type else f"  {field_name}")
            description = _field_description(info).strip()
            for desc_line in description.splitlines():
                lines.append(f"      {desc_line}")
            # Nested object fields declare their sub-attributes under `fields`.
            for sub_name, sub_info in ((info or {}).get("fields") or {}).items():
                sub_type = str((sub_info or {}).get("type", ""))
                dotted = f"{field_name}.{sub_name}"
                lines.append(f"    {dotted} ({sub_type})" if sub_type else f"    {dotted}")
                for desc_line in _field_description(sub_info).strip().splitlines():
                    lines.append(f"        {desc_line}")
        lines.append("")

    _append_field_section("Output fields", config.get("output_fields") or {})
    _append_field_section("Base output fields", config.get("base_output_fields") or {})

    return "\n".join(lines).rstrip() + "\n"


@cli.command()
@click.pass_context
@click.argument("code", type=str)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "markdown", "pretty"], case_sensitive=False),
    default="markdown",
    show_default=True,
    help="Output format for the datasource config.",
)
def get_datasource(ctx: click.Context, code: str, output_format: str):
    """Get the configuration for a single datasource by its source code (e.g. PG, PH, DTC)."""
    client = get_client(ctx)
    response_data = client.get_datasource(code=code, delegate_to=ctx.obj["delegate_to"])
    output_format = output_format.lower()
    if output_format == "json":
        click.echo(json.dumps(response_data, indent=2))
        return
    config = response_data.get("config", response_data)
    if output_format == "pretty":
        click.echo(_render_datasource_pretty(config))
    else:
        click.echo(_render_datasource_markdown(config))


def main():
    cli()


if __name__ == "__main__":
    main()
