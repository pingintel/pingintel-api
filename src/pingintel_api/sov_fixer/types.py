# Copyright 2021-2024 Ping Data Intelligence
from typing import TypedDict, NotRequired
import enum


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
