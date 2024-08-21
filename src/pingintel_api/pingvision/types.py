from typing import TypedDict


class PingVisionListActivityDetailDocumentResponse(TypedDict):
    document_type: str
    filename: str
    processing_status: str
    url: str
    created_time: str


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
    id: str
    modified_time: str
    pk: int
    source__source_type: str
    team__name: str | None
    workflow_status__name: str | None
    workflow_status_id: int | None


class PingVisionListActivityResponse(TypedDict):
    results: list[PingVisionListActivityDetailResponse]
    cursor_id: str | None
    prev_cursor_id: str | None
    # total_count: int
    # returned_count: int


class PingVisionCreateSubmissionResponse(TypedDict):
    id: str
    message: str
