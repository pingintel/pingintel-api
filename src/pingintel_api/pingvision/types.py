from typing import TypedDict


class PingVisionListActivityResponse(TypedDict):
    results: list[dict]
    cursor_id: str | None
    prev_cursor_id: str | None
    remaining_count: int
