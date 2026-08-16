from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID


class AppointmentStatus(StrEnum):
    OPEN = "open"
    BOOKED = "booked"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class Appointment:
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


class SlotNotFoundError(Exception):
    """Raised when a referenced appointment/slot does not exist."""


class SlotNotAvailableError(Exception):
    """Raised when a slot cannot be booked or deleted in its current state or time."""


class NotAppointmentOwnerError(Exception):
    """Raised when a client tries to cancel an appointment they did not book."""


class AppointmentAlreadyCancelledError(Exception):
    """Raised when cancelling an appointment that is already cancelled."""


class AppointmentRepository(Protocol):
    async def add(self, appointment: Appointment) -> Appointment: ...

    async def update(self, appointment: Appointment) -> Appointment: ...

    async def delete(self, appointment_id: UUID) -> None: ...

    async def get_by_id(self, appointment_id: UUID) -> Appointment | None: ...

    async def list_open_upcoming(self, now: datetime) -> list[Appointment]: ...

    async def list_for_client(self, client_id: UUID) -> list[Appointment]: ...

    async def list_all(self, status: AppointmentStatus | None = None) -> list[Appointment]: ...
