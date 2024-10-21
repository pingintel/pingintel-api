from typing import TypedDict, Literal, Any


class PingRadarListActivityDetailDocumentResponse(TypedDict):
    document_type: str
    filename: str
    processing_status: str
    url: str
    created_time: str
    actions: list[Literal["download", "archive", "unarchive", "sovfixer-parse"]]


class PingRadarListActivityDetailResponse(TypedDict):
    actions: dict
    claimed_by_id: str | None
    company__name: str | None
    company__short_name: str | None
    claimed_by__username: str | None
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
    ping_maps: dict[str, str | int | None]

    data_readiness_score: float
    data_readiness_notes: list[dict[str, Any]]
    global_request_id: str | None
    # extra_data
    # inception_date
    insured_name: str | None
    insured_street: str | None
    insured_city: str | None
    insured_state: str | None
    insured_zip: str | None
    insured_fein: str | None
    home_state: str | None
    # broker
    insured_business_description: str | None
    triage_rule_results: list[dict[str, str | None]]
    triage_rules_overall_result: Literal["A", "D", "C"]


class PingRadarListActivityResponse(TypedDict):
    results: list[PingRadarListActivityDetailResponse]
    cursor_id: str | None
    prev_cursor_id: str | None
    # total_count: int
    # returned_count: int


class PingRadarCreateSubmissionResponse(TypedDict):
    id: str
    message: str


class PingRadarNavResponse(TypedDict):
    items: list[dict]
    division_id: int
    group: str
