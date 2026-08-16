from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from pydantic.alias_generators import to_camel

from site_api.api.dependencies import get_current_user, get_scheduling_service
from site_api.domain.scheduling import (
    Appointment,
    AppointmentAlreadyCancelledError,
    AppointmentStatus,
    NotAppointmentOwnerError,
    SlotNotAvailableError,
    SlotNotFoundError,
)
from site_api.domain.users import AuthenticatedUser
from site_api.services.scheduling import BookSlot, SchedulingService

router = APIRouter(prefix="/scheduling", tags=["scheduling"])


class SlotSummary(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: UUID
    starts_at: datetime
    ends_at: datetime


class AppointmentDetail(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: UUID
    starts_at: datetime
    ends_at: datetime
    status: AppointmentStatus
    client_id: UUID | None
    client_name: str | None
    client_email: str | None
    notes: str | None
    created_by_admin_id: UUID
    created_at: datetime
    updated_at: datetime


class BookSlotRequest(BaseModel):
    notes: str | None = Field(default=None, max_length=2000)


def to_slot_summary(appointment: Appointment) -> SlotSummary:
    return SlotSummary(
        id=appointment.id,
        starts_at=appointment.starts_at,
        ends_at=appointment.ends_at,
    )


def to_appointment_detail(appointment: Appointment) -> AppointmentDetail:
    return AppointmentDetail(
        id=appointment.id,
        starts_at=appointment.starts_at,
        ends_at=appointment.ends_at,
        status=appointment.status,
        client_id=appointment.client_id,
        client_name=appointment.client_name,
        client_email=appointment.client_email,
        notes=appointment.notes,
        created_by_admin_id=appointment.created_by_admin_id,
        created_at=appointment.created_at,
        updated_at=appointment.updated_at,
    )


@router.get("/slots", response_model=list[SlotSummary], response_model_by_alias=True)
async def list_open_slots(
    service: Annotated[SchedulingService, Depends(get_scheduling_service)],
) -> list[SlotSummary]:
    slots = await service.list_open_upcoming_slots()
    return [to_slot_summary(slot) for slot in slots]


@router.post(
    "/slots/{slot_id}/book",
    response_model=AppointmentDetail,
    response_model_by_alias=True,
)
async def book_slot(
    slot_id: UUID,
    payload: BookSlotRequest,
    service: Annotated[SchedulingService, Depends(get_scheduling_service)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> AppointmentDetail:
    try:
        appointment = await service.book_slot(
            BookSlot(
                slot_id=slot_id,
                client_id=current_user.id,
                client_name=current_user.full_name,
                client_email=current_user.email_address,
                notes=payload.notes,
            )
        )
    except SlotNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Slot not found",
        ) from error
    except SlotNotAvailableError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This slot is no longer available",
        ) from error

    return to_appointment_detail(appointment)


@router.get(
    "/appointments/mine",
    response_model=list[AppointmentDetail],
    response_model_by_alias=True,
)
async def list_my_appointments(
    service: Annotated[SchedulingService, Depends(get_scheduling_service)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> list[AppointmentDetail]:
    appointments = await service.list_my_appointments(current_user.id)
    return [to_appointment_detail(appointment) for appointment in appointments]


@router.post(
    "/appointments/{appointment_id}/cancel",
    response_model=AppointmentDetail,
    response_model_by_alias=True,
)
async def cancel_my_appointment(
    appointment_id: UUID,
    service: Annotated[SchedulingService, Depends(get_scheduling_service)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> AppointmentDetail:
    try:
        appointment = await service.cancel_own_appointment(appointment_id, current_user.id)
    except SlotNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        ) from error
    except NotAppointmentOwnerError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only cancel your own appointments",
        ) from error
    except AppointmentAlreadyCancelledError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This appointment is already cancelled",
        ) from error

    return to_appointment_detail(appointment)
