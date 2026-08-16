from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from site_api.api.dependencies import get_testimonial_service, require_admin
from site_api.api.routes.testimonials import TestimonialDetail, to_detail
from site_api.domain.testimonials import TestimonialNotFoundError, TestimonialStatus
from site_api.services.testimonials import TestimonialService

router = APIRouter(
    prefix="/admin/testimonials",
    tags=["admin testimonials"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=list[TestimonialDetail], response_model_by_alias=True)
async def list_all_testimonials(
    service: Annotated[TestimonialService, Depends(get_testimonial_service)],
    status_filter: Annotated[TestimonialStatus | None, Query(alias="status")] = None,
) -> list[TestimonialDetail]:
    testimonials = await service.list_all(status_filter)
    return [to_detail(testimonial) for testimonial in testimonials]


@router.post(
    "/{testimonial_id}/approve",
    response_model=TestimonialDetail,
    response_model_by_alias=True,
)
async def approve_testimonial(
    testimonial_id: UUID,
    service: Annotated[TestimonialService, Depends(get_testimonial_service)],
) -> TestimonialDetail:
    try:
        testimonial = await service.approve_testimonial(testimonial_id)
    except TestimonialNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Testimonial not found",
        ) from error

    return to_detail(testimonial)


@router.post(
    "/{testimonial_id}/reject",
    response_model=TestimonialDetail,
    response_model_by_alias=True,
)
async def reject_testimonial(
    testimonial_id: UUID,
    service: Annotated[TestimonialService, Depends(get_testimonial_service)],
) -> TestimonialDetail:
    try:
        testimonial = await service.reject_testimonial(testimonial_id)
    except TestimonialNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Testimonial not found",
        ) from error

    return to_detail(testimonial)


@router.delete("/{testimonial_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_testimonial(
    testimonial_id: UUID,
    service: Annotated[TestimonialService, Depends(get_testimonial_service)],
) -> None:
    try:
        await service.delete_testimonial(testimonial_id)
    except TestimonialNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Testimonial not found",
        ) from error
