from typing import Any, Dict, List, NotRequired, Optional, TypedDict


class PingMapsStatus(TypedDict):
    status: str | None
    status_display: str | None
    status_reason: str | None
    status_pct_complete: float | None
    url: str | None
