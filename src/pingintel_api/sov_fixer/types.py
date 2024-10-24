# Copyright 2021-2024 Ping Data Intelligence
import enum
from datetime import datetime
from typing import Any, Dict, List, NotRequired, Optional, TypedDict

from ..common_types import PingMapsStatus


class SOV_STATUS(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    ENRICHING = "ENRICHING"
    REENRICHING = "REENRICHING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


INCOMPLETE_STATUSES = [
    SOV_STATUS.PENDING,
    SOV_STATUS.IN_PROGRESS,
    SOV_STATUS.ENRICHING,
    SOV_STATUS.REENRICHING,
]


class SOV_RESULT_STATUS(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED_TO_READ = "FAILED_TO_READ"
    FAILED_TO_PARSE = "FAILED_TO_PARSE"
    FAILED_TO_PROCESS = "FAILED_TO_PROCESS"


class FixSOVResponseRequest(TypedDict):
    status: SOV_STATUS
    requested_at: str
    progress_started_at: str
    completed_at: str | None
    last_health_check_time: str
    last_health_status: str
    pct_complete: int


class OutputData(TypedDict):
    label: str
    # sovid: str
    scrubbed_filename: str
    # sov_data_id: int
    output_format: str
    url: str


class FixSOVResponseResultOutput(TypedDict):
    url: str
    description: str
    filename: str


class FixSOVResponseResult(TypedDict):
    message: str
    status: SOV_RESULT_STATUS
    outputs: list[FixSOVResponseResultOutput]


class FixSOVResponse(TypedDict):
    request: FixSOVResponseRequest
    result: NotRequired[FixSOVResponseResult]


class UpdateOutputData(TypedDict):
    url: str
    output_format: str
    completed_time: datetime | None


class OutputData(TypedDict):
    label: str
    # sovid: str
    scrubbed_filename: str
    # sov_data_id: int
    output_format: str
    url: str


class UpdateData(TypedDict):
    sovid: int
    sudid: int
    filename: str
    document_type: str
    record_type: str
    sheet_name: str
    original_sovid: int | None
    posted_time: datetime
    num_rows: int
    sov_data_last_updated_date: datetime
    outputs: list[UpdateOutputData]


class SOVData(TypedDict):
    id: str | None
    document_type: str | None
    pct_complete: float | None
    filename: str | None
    status: str | None
    status_display: str | None
    last_health_status: str | None
    client_ref: str | None
    output_data: list[OutputData] | None
    origin: str | None
    organization__short_name: str | None
    global_request_id: str | None
    ping_maps_url: str | None
    input_file_url: str | None
    extra_data: dict[str, Any] | None
    updates: dict[int, UpdateData] | None
    completed_time: str | None
    created_time: str | None
    subject: str | None
    from_email: str | None
    to_email: str | None
    num_buildings: int | None
    progress_started_time: str | None
    parsing_completed_time: str | None
    pingdata_stats: dict[str, dict[str, int]] | None
    ping_maps: NotRequired[PingMapsStatus | None]
    data_readiness_score: NotRequired[int | None]
    data_readiness_notes: NotRequired[list[dict[str, str | int]] | None]


class ActivityResponse(TypedDict):
    results: list[SOVData]
    cursor_id: str | None
    prev_cursor_id: str | None
    remaining_count: int
