import datetime
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


class DOCUMENT_PROCESSING_STATUS(str, enum.Enum):
    NOT_PROCESSED = "N"
    IN_PROGRESS = "I"
    COMPLETED = "C"
    FAILED = "F"


class PingVisionListActivityDetailJobResponse(TypedDict):
    job_id: str
    filenames: list[str] | None
    user_id: int
    job_type: Literal["SOVFIXER", "AIR", "RMS"]
    created_time: str
    updated_time: str
    processing_status: DOCUMENT_PROCESSING_STATUS
    processing_pct_complete: NotRequired[float | None]
    processing_last_message: NotRequired[str | None]
    job_type_details: NotRequired[PingVisionListActivityDetailJobSovFixerDetailResponse]


class PingVisionListActivityDetailResponse(TypedDict):
    actions: dict
    claimed_by_id: str | None
    company_name: str | None
    company_short_name: str | None
    created_time: str
    division_uuid: str
    division_name: str
    division_short_name: str
    division_id: int
    documents: list[PingVisionListActivityDetailDocumentResponse]
    jobs: list[PingVisionListActivityDetailJobResponse]
    id: str
    modified_time: str
    pk: int
    team_uuid: str
    team_name: str | None
    workflow_status_name: str | None
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


class SUBMISSION_STATUS_CATEGORY(str, enum.Enum):
    RECEIVED = "R"
    AUTOMATED_PROCESSING = "A"
    READY = "Y"
    IN_PROGRESS = "I"
    ON_HOLD = "H"
    COMPLETED = "C"
    CLOSED = "L"


class PingVisionListSubmissionStatusItemResponse(TypedDict):
    category: SUBMISSION_STATUS_CATEGORY
    uuid: str
    name: str


class PingVisionChangeSubmissionStatusResponse(TypedDict): ...


class PingVisionSubmissionBulkUpdateUpdatedData(TypedDict):
    claimed_by_id: NotRequired[int]
    workflow_status_id: NotRequired[int]


class PingVisionSubmissionBulkUpdateResponse(TypedDict):
    id: str
    updated_data: PingVisionSubmissionBulkUpdateUpdatedData
    error: NotRequired[str]


class PingVisionSubmissionBulkUpdateChangeItem(TypedDict):
    action: Literal["claim", "change_status"]
    parameters: dict[Literal["claimed_by_id", "workflow_status_id"], int]


class SUBMISSION_EVENT_LOG_TYPE(str, enum.Enum):
    NEW_SUBMISSION = "NEW"
    SUBMISSION_STATUS_CHANGE = "SSC"
    USER_COMMENT = "UC"
    SYSTEM_NOTE = "SN"
    CLAIMED_BY_CHANGE = "CBC"
    SOV_FIXER_INVOKED = "SFI"
    SOV_FIXER_RESULTS_RECEIVED = "SFRR"
    SOV_FIXER_FAILED = "SFF"
    SOV_FIXER_UPDATE_RECEIVED = "SFUR"
    ERROR = "ERR"
    SCRUBBING_COMPLETE = "SCC"


class PingVisionSubmissionEventResponse(TypedDict):
    uuid: str
    division_uuid: str
    team_uuid: str
    user_id: int
    pingid: str
    message: str
    event_type: SUBMISSION_EVENT_LOG_TYPE
    created_time: str
    old_value: str | int
    new_value: str | int


class PingVisionSubmissionEventsResponse(TypedDict):
    results: list[PingVisionSubmissionEventResponse]
    cursor_id: str


class PingVisionSubmissionEventsRequest(TypedDict):
    pingid: NotRequired[str | None]
    division: NotRequired[str | None]
    team: NotRequired[str | None]
    start: NotRequired[datetime.datetime | None]
    cursor_id: NotRequired[str | None]
    page_size: NotRequired[int | None]


class PingVisionTeamsResponse(TypedDict):
    team_uuid: str
    team_name: str
    division_uuid: str
    division_name: str
    company_uuid: str
    company_name: str

    membership_type: Literal["member", "admin", "owner"]


class DATA_ITEM_ACTIONS(str, enum.Enum):
    UPSERT = "upsert"
    REPLACE = "replace"
