from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from site_api.api.dependencies import get_current_user, get_testimonial_service
from site_api.domain.testimonials import Testimonial, TestimonialStatus
from site_api.domain.users import AuthenticatedUser
from site_api.services.testimonials import SubmitTestimonial, TestimonialService

router = APIRouter(prefix="/testimonials", tags=["testimonials"])

DEFAULT_HOMEPAGE_LIMIT = 10


class TestimonialSummary(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: UUID
    customer_name: str
    rating: int
    body: str
    created_at: datetime


class TestimonialDetail(TestimonialSummary):
    status: TestimonialStatus
    updated_at: datetime


class SubmitTestimonialRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    rating: int = Field(ge=1, le=5)
    body: str = Field(min_length=1, max_length=2000)


def to_summary(testimonial: Testimonial) -> TestimonialSummary:
    return TestimonialSummary(
        id=testimonial.id,
        customer_name=testimonial.customer_name,
        rating=testimonial.rating,
        body=testimonial.body,
        created_at=testimonial.created_at,
    )


def to_detail(testimonial: Testimonial) -> TestimonialDetail:
    return TestimonialDetail(
        id=testimonial.id,
        customer_name=testimonial.customer_name,
        rating=testimonial.rating,
        body=testimonial.body,
        created_at=testimonial.created_at,
        status=testimonial.status,
        updated_at=testimonial.updated_at,
    )


@router.get("", response_model=list[TestimonialSummary], response_model_by_alias=True)
async def list_approved_testimonials(
    service: Annotated[TestimonialService, Depends(get_testimonial_service)],
    limit: Annotated[int, Query(ge=1, le=50)] = DEFAULT_HOMEPAGE_LIMIT,
) -> list[TestimonialSummary]:
    testimonials = await service.list_approved(limit)
    return [to_summary(testimonial) for testimonial in testimonials]


@router.get("/mine", response_model=TestimonialDetail | None, response_model_by_alias=True)
async def get_my_testimonial(
    service: Annotated[TestimonialService, Depends(get_testimonial_service)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> TestimonialDetail | None:
    testimonial = await service.get_my_testimonial(current_user.id)
    return None if testimonial is None else to_detail(testimonial)


@router.post(
    "/mine",
    response_model=TestimonialDetail,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
)
async def submit_my_testimonial(
    payload: SubmitTestimonialRequest,
    service: Annotated[TestimonialService, Depends(get_testimonial_service)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> TestimonialDetail:
    testimonial = await service.submit_testimonial(
        SubmitTestimonial(
            customer_id=current_user.id,
            customer_name=current_user.full_name,
            rating=payload.rating,
            body=payload.body,
        )
    )
    return to_detail(testimonial)
