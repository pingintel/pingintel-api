from typing import TypedDict, NotRequired, Literal

from ..common_types import PingMapsStatus


class PingRadarListActivityDetailDocumentResponse(TypedDict):
    document_type: str
    filename: str
    url: str
    preview_url: str | None # non null for documents like .docx that use pdf type as preview
    created_time: str
    is_archived: bool
    archived_on: str | None
    archived_reason: str | None
    actions: list[str]
    extension: str | None
    size: int | None


class PingRadarListActivityDetailJobSovFixerDetailResponse(TypedDict):
    sovfixer_sovid: NotRequired[str | None]
    sovfixer_result_status: NotRequired[str | None]
    sovfixer_result_message: NotRequired[str | None]


class PingRadarListActivityDetailJobResponse(TypedDict):
    job_id: str
    filenames: list[str] | None
    user_id: int
    job_type: Literal["SOVFIXER", "AIR", "RMS"]
    created_time: str
    updated_time: str
    processing_status: str
    processing_pct_complete: NotRequired[float | None]
    processing_last_message: NotRequired[str | None]
    job_type_details: NotRequired[PingRadarListActivityDetailJobSovFixerDetailResponse]


class PingRadarListActivityDetailResponse(TypedDict):
    actions: dict
    claimed_by_id: str | None
    company__name: str | None
    company__short_name: str | None
    created_time: str
    division__name: str
    division__short_name: str
    division_id: int
    documents: list[PingRadarListActivityDetailDocumentResponse]
    jobs: list[PingRadarListActivityDetailJobResponse]
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


class PingRadarListActivityResponse(TypedDict):
    results: list[PingRadarListActivityDetailResponse]
    cursor_id: str | None
    prev_cursor_id: str | None
    # total_count: int
    # returned_count: int


class PingRadarCreateSubmissionResponse(TypedDict):
    id: str
    message: str
    url: str
