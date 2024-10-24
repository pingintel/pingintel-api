from typing import TypedDict, NotRequired

from ..common_types import PingMapsStatus


class PingRadarListActivityDetailDocumentResponse(TypedDict):
    document_type: str
    filename: str
    processing_status: str
    url: str
    created_time: str


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
    id: str
    modified_time: str
    pk: int
    source__source_type: str
    team__name: str | None
    workflow_status__name: str | None
    workflow_status_id: int | None
    ping_maps: NotRequired[PingMapsStatus | None]


class PingRadarListActivityResponse(TypedDict):
    results: list[PingRadarListActivityDetailResponse]
    cursor_id: str | None
    prev_cursor_id: str | None
    # total_count: int
    # returned_count: int


class PingRadarCreateSubmissionResponse(TypedDict):
    id: str
    message: str
