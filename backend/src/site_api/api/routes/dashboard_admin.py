from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from site_api.api.dependencies import get_dashboard_service, require_admin
from site_api.services.dashboard import ActivityItem, DashboardService, DashboardSummary

router = APIRouter(
    prefix="/admin/dashboard",
    tags=["admin dashboard"],
    dependencies=[Depends(require_admin)],
)


class ActivityItemResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    activity_type: str
    id: UUID
    label: str
    occurred_at: datetime


class DashboardSummaryResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    new_leads_today: int
    new_leads_this_week: int
    upcoming_appointments: int
    revenue_this_week_cents: int
    revenue_this_month_cents: int
    pending_testimonials: int
    leads_needing_follow_up: int
    recent_activity: list[ActivityItemResponse]


def _to_activity_response(item: ActivityItem) -> ActivityItemResponse:
    return ActivityItemResponse(
        activity_type=item.activity_type,
        id=item.id,
        label=item.label,
        occurred_at=item.occurred_at,
    )


def to_summary_response(summary: DashboardSummary) -> DashboardSummaryResponse:
    return DashboardSummaryResponse(
        new_leads_today=summary.new_leads_today,
        new_leads_this_week=summary.new_leads_this_week,
        upcoming_appointments=summary.upcoming_appointments,
        revenue_this_week_cents=summary.revenue_this_week_cents,
        revenue_this_month_cents=summary.revenue_this_month_cents,
        pending_testimonials=summary.pending_testimonials,
        leads_needing_follow_up=summary.leads_needing_follow_up,
        recent_activity=[_to_activity_response(item) for item in summary.recent_activity],
    )


@router.get("/summary", response_model=DashboardSummaryResponse, response_model_by_alias=True)
async def get_dashboard_summary(
    service: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> DashboardSummaryResponse:
    summary = await service.get_summary()
    return to_summary_response(summary)
