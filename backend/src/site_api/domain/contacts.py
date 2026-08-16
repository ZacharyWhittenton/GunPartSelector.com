from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID


class ContactRequestStatus(StrEnum):
    RECEIVED = "received"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    WON = "won"
    LOST = "lost"


@dataclass(frozen=True, slots=True)
class ContactRequest:
    id: UUID
    name: str
    email_address: str
    company: str | None
    phone: str | None
    service: str
    message: str
    status: ContactRequestStatus
    created_at: datetime
    updated_at: datetime
    follow_up_at: datetime | None


class ContactRequestNotFoundError(Exception):
    """Raised when a referenced contact request does not exist."""


class ContactRequestRepository(Protocol):
    async def add(self, contact_request: ContactRequest) -> ContactRequest: ...

    async def update(self, contact_request: ContactRequest) -> ContactRequest: ...

    async def get_by_id(self, contact_request_id: UUID) -> ContactRequest | None: ...

    async def list_all(
        self, status: ContactRequestStatus | None = None
    ) -> list[ContactRequest]: ...
