from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from site_api.api.dependencies import get_analytics_service
from site_api.domain.analytics import InvalidClickPositionError
from site_api.services.analytics import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


class PageViewRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    path: str = Field(min_length=1, max_length=500)
    referrer: str | None = Field(default=None, max_length=500)
    session_id: str = Field(min_length=1, max_length=100)


class ClickRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    path: str = Field(min_length=1, max_length=500)
    x_percent: float = Field(ge=0, le=100)
    y_percent: float = Field(ge=0, le=100)
    element_label: str | None = Field(default=None, max_length=200)
    session_id: str = Field(min_length=1, max_length=100)


@router.post("/pageview", status_code=status.HTTP_204_NO_CONTENT)
async def track_page_view(
    payload: PageViewRequest,
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
) -> None:
    await service.track_page_view(payload.path, payload.referrer, payload.session_id)


@router.post("/click", status_code=status.HTTP_204_NO_CONTENT)
async def track_click(
    payload: ClickRequest,
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
) -> None:
    try:
        await service.track_click(
            payload.path,
            payload.x_percent,
            payload.y_percent,
            payload.element_label,
            payload.session_id,
        )
    except InvalidClickPositionError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Click position must be within 0-100 percent",
        ) from error
