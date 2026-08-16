from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PageViewEvent:
    id: UUID
    path: str
    referrer: str | None
    session_id: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ClickEvent:
    id: UUID
    path: str
    x_percent: float
    y_percent: float
    element_label: str | None
    session_id: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class PageViewSummary:
    path: str
    view_count: int
    unique_sessions: int


class InvalidClickPositionError(Exception):
    """Raised when a click event's normalized position is outside 0-100."""


class AnalyticsRepository(Protocol):
    async def record_page_view(self, event: PageViewEvent) -> PageViewEvent: ...

    async def record_click(self, event: ClickEvent) -> ClickEvent: ...

    async def top_pages(self, since: datetime, limit: int) -> list[PageViewSummary]: ...

    async def click_points(self, path: str, since: datetime) -> list[ClickEvent]: ...
