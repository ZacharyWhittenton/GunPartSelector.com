from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, model_validator

from pydantic.alias_generators import to_camel

from site_api.api.dependencies import get_scheduling_service, require_admin
from site_api.api.routes.scheduling import AppointmentDetail, to_appointment_detail
from site_api.domain.scheduling import (
    AppointmentAlreadyCancelledError,
    AppointmentStatus,
    SlotNotAvailableError,
    SlotNotFoundError,
)
from site_api.domain.users import AuthenticatedUser
from site_api.services.scheduling import CreateSlot, SchedulingService

router = APIRouter(
    prefix="/admin/scheduling", tags=["admin scheduling"], dependencies=[Depends(require_admin)]
)


class CreateSlotRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    starts_at: datetime
    ends_at: datetime

    @model_validator(mode="after")
    def _ends_after_starts(self) -> "CreateSlotRequest":
        if self.ends_at <= self.starts_at:
            raise ValueError("endsAt must be after startsAt")
        return self


@router.post(
    "/slots",
    response_model=AppointmentDetail,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
)
async def create_slot(
    payload: CreateSlotRequest,
    service: Annotated[SchedulingService, Depends(get_scheduling_service)],
    current_user: Annotated[AuthenticatedUser, Depends(require_admin)],
) -> AppointmentDetail:
    try:
        appointment = await service.create_slot(
            CreateSlot(
                starts_at=payload.starts_at,
                ends_at=payload.ends_at,
                created_by_admin_id=current_user.id,
            )
        )
    except SlotNotAvailableError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Slot start time must be in the future",
        ) from error

    return to_appointment_detail(appointment)


@router.get(
    "/appointments",
    response_model=list[AppointmentDetail],
    response_model_by_alias=True,
)
async def list_appointments(
    service: Annotated[SchedulingService, Depends(get_scheduling_service)],
    status_filter: Annotated[AppointmentStatus | None, Query(alias="status")] = None,
) -> list[AppointmentDetail]:
    appointments = await service.list_all_appointments(status_filter)
    return [to_appointment_detail(appointment) for appointment in appointments]


@router.post(
    "/appointments/{appointment_id}/cancel",
    response_model=AppointmentDetail,
    response_model_by_alias=True,
)
async def cancel_appointment(
    appointment_id: UUID,
    service: Annotated[SchedulingService, Depends(get_scheduling_service)],
) -> AppointmentDetail:
    try:
        appointment = await service.admin_cancel_appointment(appointment_id)
    except SlotNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        ) from error
    except AppointmentAlreadyCancelledError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This appointment is already cancelled",
        ) from error

    return to_appointment_detail(appointment)


@router.delete("/slots/{slot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_slot(
    slot_id: UUID,
    service: Annotated[SchedulingService, Depends(get_scheduling_service)],
) -> None:
    try:
        await service.delete_slot(slot_id)
    except SlotNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Slot not found",
        ) from error
    except SlotNotAvailableError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only open slots can be deleted; cancel booked appointments instead",
        ) from error
