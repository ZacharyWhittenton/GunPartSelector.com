from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from loguru import logger

from site_api.domain.scheduling import (
    Appointment,
    AppointmentAlreadyCancelledError,
    AppointmentRepository,
    AppointmentStatus,
    NotAppointmentOwnerError,
    SlotNotAvailableError,
    SlotNotFoundError,
)
from site_api.services.email import EmailService


@dataclass(frozen=True, slots=True)
class CreateSlot:
    starts_at: datetime
    ends_at: datetime
    created_by_admin_id: UUID


@dataclass(frozen=True, slots=True)
class BookSlot:
    slot_id: UUID
    client_id: UUID
    client_name: str
    client_email: str
    notes: str | None


class SchedulingService:
    def __init__(
        self,
        repository: AppointmentRepository,
        email_service: EmailService | None = None,
        id_factory: Callable[[], UUID] = uuid4,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._repository = repository
        self._email = email_service or EmailService(None, None, None)
        self._id_factory = id_factory
        self._clock = clock

    async def create_slot(self, command: CreateSlot) -> Appointment:
        now = self._clock()
        if command.starts_at < now:
            raise SlotNotAvailableError

        appointment = Appointment(
            id=self._id_factory(),
            starts_at=command.starts_at,
            ends_at=command.ends_at,
            status=AppointmentStatus.OPEN,
            client_id=None,
            client_name=None,
            client_email=None,
            notes=None,
            created_by_admin_id=command.created_by_admin_id,
            created_at=now,
            updated_at=now,
        )
        saved = await self._repository.add(appointment)
        logger.bind(appointment_id=str(saved.id)).info("Appointment slot created")
        return saved

    async def list_open_upcoming_slots(self) -> list[Appointment]:
        return await self._repository.list_open_upcoming(self._clock())

    async def book_slot(self, command: BookSlot) -> Appointment:
        appointment = await self._repository.get_by_id(command.slot_id)
        if appointment is None:
            raise SlotNotFoundError

        if appointment.status is not AppointmentStatus.OPEN:
            raise SlotNotAvailableError

        if appointment.starts_at < self._clock():
            raise SlotNotAvailableError

        booked = replace(
            appointment,
            status=AppointmentStatus.BOOKED,
            client_id=command.client_id,
            client_name=command.client_name,
            client_email=command.client_email,
            notes=command.notes,
            updated_at=self._clock(),
        )
        saved = await self._repository.update(booked)
        logger.bind(appointment_id=str(saved.id), client_id=str(command.client_id)).info(
            "Appointment booked"
        )
        await self._email.send_appointment_confirmation(saved)
        await self._email.notify_admin_new_appointment(saved)
        return saved

    async def list_my_appointments(self, client_id: UUID) -> list[Appointment]:
        return await self._repository.list_for_client(client_id)

    async def cancel_own_appointment(self, appointment_id: UUID, client_id: UUID) -> Appointment:
        appointment = await self._repository.get_by_id(appointment_id)
        if appointment is None:
            raise SlotNotFoundError

        if appointment.client_id != client_id:
            raise NotAppointmentOwnerError

        return await self._cancel(appointment)

    async def list_all_appointments(
        self, status: AppointmentStatus | None = None
    ) -> list[Appointment]:
        return await self._repository.list_all(status)

    async def admin_cancel_appointment(self, appointment_id: UUID) -> Appointment:
        appointment = await self._repository.get_by_id(appointment_id)
        if appointment is None:
            raise SlotNotFoundError

        return await self._cancel(appointment)

    async def delete_slot(self, slot_id: UUID) -> None:
        appointment = await self._repository.get_by_id(slot_id)
        if appointment is None:
            raise SlotNotFoundError

        if appointment.status is not AppointmentStatus.OPEN:
            raise SlotNotAvailableError

        await self._repository.delete(slot_id)
        logger.bind(appointment_id=str(slot_id)).info("Appointment slot deleted")

    async def _cancel(self, appointment: Appointment) -> Appointment:
        if appointment.status is AppointmentStatus.CANCELLED:
            raise AppointmentAlreadyCancelledError

        cancelled = replace(
            appointment,
            status=AppointmentStatus.CANCELLED,
            updated_at=self._clock(),
        )
        saved = await self._repository.update(cancelled)
        logger.bind(appointment_id=str(saved.id)).info("Appointment cancelled")
        return saved
