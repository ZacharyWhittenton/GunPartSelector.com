from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from site_api.db.models import ClickEventRecord
from site_api.db.repositories import SqlAlchemyAnalyticsRepository
from site_api.domain.analytics import ClickEvent, PageViewEvent

PAGE_VIEW_ID = UUID("9a53d09a-f258-4b09-9fb3-ef6df4c2f9fd")
CLICK_ID = UUID("1b3c4d5e-6f70-4a1b-9c2d-3e4f5a6b7c8d")
NOW = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)


class _Row:
    def __init__(self, path: str, view_count: int, unique_sessions: int) -> None:
        self.path = path
        self.view_count = view_count
        self.unique_sessions = unique_sessions


class FakeSession:
    def __init__(self, rows: list[object] | None = None) -> None:
        self.added: list[object] = []
        self.flushed = False
        self._rows = rows or []

    def add(self, record: object) -> None:
        self.added.append(record)

    async def flush(self) -> None:
        self.flushed = True

    async def execute(self, _statement: object) -> _Result:
        return _Result(self._rows)


class _Result:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def all(self) -> list[object]:
        return self._rows

    def scalars(self) -> _Scalars:
        return _Scalars(self._rows)


class _Scalars:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def all(self) -> list[object]:
        return self._values


@pytest.mark.asyncio
async def test_record_page_view_adds_and_flushes() -> None:
    session = FakeSession()
    repository = SqlAlchemyAnalyticsRepository(cast(AsyncSession, session))
    event = PageViewEvent(
        id=PAGE_VIEW_ID, path="/marketplace", referrer=None, session_id="session-1", created_at=NOW
    )

    result = await repository.record_page_view(event)

    assert result is event
    assert session.flushed is True
    assert session.added[0].path == "/marketplace"


@pytest.mark.asyncio
async def test_record_click_adds_and_flushes() -> None:
    session = FakeSession()
    repository = SqlAlchemyAnalyticsRepository(cast(AsyncSession, session))
    event = ClickEvent(
        id=CLICK_ID,
        path="/marketplace",
        x_percent=42.5,
        y_percent=88.0,
        element_label="Add to Cart",
        session_id="session-1",
        created_at=NOW,
    )

    result = await repository.record_click(event)

    assert result is event
    assert session.flushed is True
    record = session.added[0]
    assert record.x_percent == 42.5
    assert record.element_label == "Add to Cart"


@pytest.mark.asyncio
async def test_top_pages_maps_rows() -> None:
    session = FakeSession(rows=[_Row("/", 5, 3), _Row("/marketplace", 2, 2)])
    repository = SqlAlchemyAnalyticsRepository(cast(AsyncSession, session))

    summaries = await repository.top_pages(NOW, 20)

    assert [summary.path for summary in summaries] == ["/", "/marketplace"]
    assert summaries[0].view_count == 5
    assert summaries[0].unique_sessions == 3


@pytest.mark.asyncio
async def test_click_points_maps_records() -> None:
    record = ClickEventRecord(
        id=CLICK_ID,
        path="/marketplace",
        x_percent=10.0,
        y_percent=20.0,
        element_label="Header",
        session_id="session-1",
        created_at=NOW,
    )
    session = FakeSession(rows=[record])
    repository = SqlAlchemyAnalyticsRepository(cast(AsyncSession, session))

    points = await repository.click_points("/marketplace", NOW)

    assert len(points) == 1
    assert points[0].element_label == "Header"
