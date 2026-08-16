from datetime import UTC, datetime
from itertools import count
from uuid import UUID

import pytest

from site_api.domain.analytics import InvalidClickPositionError
from site_api.services.analytics import AnalyticsService
from tests.conftest import InMemoryAnalyticsRepository

NOW = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)


@pytest.fixture
def service(analytics_repository: InMemoryAnalyticsRepository) -> AnalyticsService:
    ids = iter(UUID(int=n) for n in count(1))
    return AnalyticsService(analytics_repository, id_factory=lambda: next(ids), clock=lambda: NOW)


@pytest.mark.asyncio
async def test_track_page_view_records_event(service: AnalyticsService) -> None:
    event = await service.track_page_view("/marketplace", "https://google.com", "session-1")

    assert event.path == "/marketplace"
    assert event.referrer == "https://google.com"
    assert event.session_id == "session-1"
    assert event.created_at == NOW


@pytest.mark.asyncio
async def test_track_click_records_event(service: AnalyticsService) -> None:
    event = await service.track_click("/marketplace", 42.5, 88.0, "Add to Cart", "session-1")

    assert event.x_percent == 42.5
    assert event.y_percent == 88.0
    assert event.element_label == "Add to Cart"


@pytest.mark.asyncio
async def test_track_click_rejects_out_of_range_position(service: AnalyticsService) -> None:
    with pytest.raises(InvalidClickPositionError):
        await service.track_click("/marketplace", 101, 50, None, "session-1")

    with pytest.raises(InvalidClickPositionError):
        await service.track_click("/marketplace", 50, -1, None, "session-1")


@pytest.mark.asyncio
async def test_get_top_pages_ranks_by_view_count(service: AnalyticsService) -> None:
    await service.track_page_view("/", None, "session-1")
    await service.track_page_view("/", None, "session-2")
    await service.track_page_view("/marketplace", None, "session-1")

    pages = await service.get_top_pages()

    assert pages[0].path == "/"
    assert pages[0].view_count == 2
    assert pages[0].unique_sessions == 2
    assert pages[1].path == "/marketplace"
    assert pages[1].view_count == 1


@pytest.mark.asyncio
async def test_get_top_pages_excludes_events_outside_window(
    service: AnalyticsService, analytics_repository: InMemoryAnalyticsRepository
) -> None:
    from dataclasses import replace

    old_event = await service.track_page_view("/", None, "session-1")
    analytics_repository.page_views[0] = replace(
        old_event, created_at=datetime(2020, 1, 1, tzinfo=UTC)
    )

    pages = await service.get_top_pages(days=30)

    assert pages == []


@pytest.mark.asyncio
async def test_get_click_heatmap_returns_points_for_path(service: AnalyticsService) -> None:
    await service.track_click("/marketplace", 10, 20, "Header", "session-1")
    await service.track_click("/", 30, 40, "Nav", "session-1")

    points = await service.get_click_heatmap("/marketplace")

    assert len(points) == 1
    assert points[0].element_label == "Header"
