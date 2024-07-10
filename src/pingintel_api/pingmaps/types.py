from typing import Any, Dict, List, NotRequired, Optional, TypedDict


class PingMapsPolicyLocationResponse(TypedDict):
    pass
    # results: list[dict]
    # cursor_id: str | None
    # prev_cursor_id: str | None
    # total_count: int
    # returned_count: int


class PingMapsPolicyLocationRequest(TypedDict):
    sovid: str
    lat1: NotRequired[float]
    lat2: NotRequired[float]
    lng1: NotRequired[float]
    lng2: NotRequired[float]
    limit: NotRequired[int]
    show_points_sooner: NotRequired[bool]

    wind_tier: NotRequired[str]
    occupancy__code_air: NotRequired[int]
    occupancy__code_rms: NotRequired[int]
    occupancy__code_atc: NotRequired[int]

    const__code_air: NotRequired[int]
    const__code_rms: NotRequired[int]
    const__code_iso: NotRequired[int]
    # const__desc_ping: NotRequired[str]

    const__bldg_year_built__gte: NotRequired[int]
    const__bldg_year_built__lte: NotRequired[int]
    const__bldg_year_built__bins: NotRequired[str | list[str]]
    fema_flood_zone: NotRequired[str]
    occupancy__desc_ping: NotRequired[str]

    limits__total_limit__gte: NotRequired[int]
    limits__total_limit__lte: NotRequired[int]

    attach: NotRequired[int]
    layer_limit: NotRequired[int]


class PingMapsPolicyBreakdownRequest(PingMapsPolicyLocationRequest):
    fields: NotRequired[list[str]]
