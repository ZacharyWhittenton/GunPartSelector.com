from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from site_api.domain.analytics import (
    AnalyticsRepository,
    ClickEvent,
    InvalidClickPositionError,
    PageViewEvent,
    PageViewSummary,
)

DEFAULT_WINDOW_DAYS = 30
DEFAULT_TOP_PAGES_LIMIT = 20


class AnalyticsService:
    def __init__(
        self,
        repository: AnalyticsRepository,
        id_factory: Callable[[], UUID] = uuid4,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._repository = repository
        self._id_factory = id_factory
        self._clock = clock

    async def track_page_view(
        self, path: str, referrer: str | None, session_id: str
    ) -> PageViewEvent:
        event = PageViewEvent(
            id=self._id_factory(),
            path=path,
            referrer=referrer,
            session_id=session_id,
            created_at=self._clock(),
        )
        return await self._repository.record_page_view(event)

    async def track_click(
        self,
        path: str,
        x_percent: float,
        y_percent: float,
        element_label: str | None,
        session_id: str,
    ) -> ClickEvent:
        if not (0 <= x_percent <= 100) or not (0 <= y_percent <= 100):
            raise InvalidClickPositionError

        event = ClickEvent(
            id=self._id_factory(),
            path=path,
            x_percent=x_percent,
            y_percent=y_percent,
            element_label=element_label,
            session_id=session_id,
            created_at=self._clock(),
        )
        return await self._repository.record_click(event)

    async def get_top_pages(
        self, days: int = DEFAULT_WINDOW_DAYS, limit: int = DEFAULT_TOP_PAGES_LIMIT
    ) -> list[PageViewSummary]:
        since = self._clock() - timedelta(days=days)
        return await self._repository.top_pages(since, limit)

    async def get_click_heatmap(
        self, path: str, days: int = DEFAULT_WINDOW_DAYS
    ) -> list[ClickEvent]:
        since = self._clock() - timedelta(days=days)
        return await self._repository.click_points(path, since)
