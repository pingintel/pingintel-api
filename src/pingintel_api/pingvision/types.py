import enum
from typing import Any, Self, TypedDict, NotRequired, Literal

from ..common_types import PingMapsStatus


class UI_VIEW_TYPES(str, enum.Enum):
    LIST = "LIST"
    TRIAGE = "TRIAGE"
    SETTINGS = "SETTINGS"
    USER_CUSTOM = "USER_CUSTOM"


class PingVisionListActivityDetailDocumentResponse(TypedDict):
    document_type: str
    filename: str
    url: str
    preview_url: str | None  # non null for documents like .docx that use pdf type as preview
    created_time: str
    is_archived: bool
    archived_on: str | None
    archived_reason: str | None
    actions: list[str]
    extension: str | None
    size: int | None


class PingVisionListActivityDetailJobSovFixerDetailResponse(TypedDict):
    sovfixer_sovid: NotRequired[str | None]
    sovfixer_result_status: NotRequired[str | None]
    sovfixer_result_message: NotRequired[str | None]


class PingVisionListActivityDetailJobResponse(TypedDict):
    job_id: str
    filenames: list[str] | None
    user_id: int
    job_type: Literal["SOVFIXER", "AIR", "RMS"]
    created_time: str
    updated_time: str
    processing_status: str
    processing_pct_complete: NotRequired[float | None]
    processing_last_message: NotRequired[str | None]
    job_type_details: NotRequired[PingVisionListActivityDetailJobSovFixerDetailResponse]


class PingVisionListActivityDetailResponse(TypedDict):
    actions: dict
    claimed_by_id: str | None
    company__name: str | None
    company__short_name: str | None
    created_time: str
    division__name: str
    division__short_name: str
    division_id: int
    documents: list[PingVisionListActivityDetailDocumentResponse]
    jobs: list[PingVisionListActivityDetailJobResponse]
    id: str
    modified_time: str
    pk: int
    team__name: str | None
    workflow_status__name: str | None
    workflow_status_id: int | None
    ping_maps: NotRequired[PingMapsStatus | None]
    source__source_type: str | None
    source__source_type_display: str | None
    source__inbox_email_address: str | None
    triage_rule_results: list[dict[str, str | int | float]] | None


class PingVisionListActivityResponse(TypedDict):
    results: list[PingVisionListActivityDetailResponse]
    cursor_id: str | None
    prev_cursor_id: str | None
    # total_count: int
    # returned_count: int


class PingVisionCreateSubmissionResponse(TypedDict):
    id: str
    message: str
    url: str


# move to pingintel types when done
class PingVisionHistoryAPIResponseItem(TypedDict):
    uid: str
    actor_id: int
    actor_username: str
    timestamp: str  # isoformat
    verb: NotRequired[str]
    messages: list[str | dict[Literal["field", "to_value"], Any]]
    metadata: NotRequired[dict[str, Any]]


### These types should go in pingintel_api when they're done being tweaked
class PingVisionNavItemResponse(TypedDict):
    team_id: NotRequired[int]
    slug: str
    name: str
    view_type: UI_VIEW_TYPES
    description: str
    filter: NotRequired[dict[str, Any]]
    icon: NotRequired[str]
    group_by: NotRequired[str]
    order_by: NotRequired[str]
    count: NotRequired[str]


class PingVisionNavGroupResponse(TypedDict):
    items: list[PingVisionNavItemResponse | Self]
    # division_id: int
    name: str
    icon: NotRequired[str]


class PingVisionNavResponse(TypedDict):
    views: list[PingVisionNavGroupResponse | PingVisionNavItemResponse]
