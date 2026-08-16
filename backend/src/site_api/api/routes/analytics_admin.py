from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from site_api.api.dependencies import get_analytics_service, require_admin
from site_api.domain.analytics import ClickEvent, PageViewSummary
from site_api.services.analytics import AnalyticsService

router = APIRouter(
    prefix="/admin/analytics",
    tags=["admin analytics"],
    dependencies=[Depends(require_admin)],
)


class PageViewSummaryResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    path: str
    view_count: int
    unique_sessions: int


class ClickPointResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    x_percent: float
    y_percent: float
    element_label: str | None
    created_at: datetime


def _to_summary_response(summary: PageViewSummary) -> PageViewSummaryResponse:
    return PageViewSummaryResponse(
        path=summary.path,
        view_count=summary.view_count,
        unique_sessions=summary.unique_sessions,
    )


def _to_click_response(click: ClickEvent) -> ClickPointResponse:
    return ClickPointResponse(
        x_percent=click.x_percent,
        y_percent=click.y_percent,
        element_label=click.element_label,
        created_at=click.created_at,
    )


@router.get("/pages", response_model=list[PageViewSummaryResponse], response_model_by_alias=True)
async def get_top_pages(
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[PageViewSummaryResponse]:
    summaries = await service.get_top_pages(days=days, limit=limit)
    return [_to_summary_response(summary) for summary in summaries]


@router.get("/heatmap", response_model=list[ClickPointResponse], response_model_by_alias=True)
async def get_click_heatmap(
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    path: str,
    days: int = Query(default=30, ge=1, le=365),
) -> list[ClickPointResponse]:
    clicks = await service.get_click_heatmap(path, days=days)
    return [_to_click_response(click) for click in clicks]
