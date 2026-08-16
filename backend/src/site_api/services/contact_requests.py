from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from loguru import logger

from site_api.domain.contacts import (
    ContactRequest,
    ContactRequestNotFoundError,
    ContactRequestRepository,
    ContactRequestStatus,
)
from site_api.domain.lead_notes import LeadNote, LeadNoteRepository
from site_api.services.email import EmailService


@dataclass(frozen=True, slots=True)
class SubmitContactRequest:
    name: str
    email_address: str
    company: str | None
    phone: str | None
    service: str
    message: str


@dataclass(frozen=True, slots=True)
class AddLeadNote:
    lead_id: UUID
    author_id: UUID
    author_name: str
    body: str


class ContactRequestService:
    def __init__(
        self,
        repository: ContactRequestRepository,
        note_repository: LeadNoteRepository,
        email_service: EmailService | None = None,
        id_factory: Callable[[], UUID] = uuid4,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._repository = repository
        self._notes = note_repository
        self._email = email_service or EmailService(None, None, None)
        self._id_factory = id_factory
        self._clock = clock

    async def submit(self, command: SubmitContactRequest) -> ContactRequest:
        now = self._clock()
        contact_request = ContactRequest(
            id=self._id_factory(),
            name=command.name,
            email_address=command.email_address,
            company=command.company,
            phone=command.phone,
            service=command.service,
            message=command.message,
            status=ContactRequestStatus.RECEIVED,
            created_at=now,
            updated_at=now,
            follow_up_at=None,
        )
        saved_request = await self._repository.add(contact_request)
        logger.bind(contact_request_id=str(saved_request.id)).info("Contact request received")
        await self._email.notify_admin_new_lead(saved_request)
        return saved_request

    async def list_all(self, status: ContactRequestStatus | None = None) -> list[ContactRequest]:
        return await self._repository.list_all(status)

    async def get_by_id(self, contact_request_id: UUID) -> ContactRequest:
        contact_request = await self._repository.get_by_id(contact_request_id)
        if contact_request is None:
            raise ContactRequestNotFoundError
        return contact_request

    async def update_status(
        self, contact_request_id: UUID, status: ContactRequestStatus
    ) -> ContactRequest:
        contact_request = await self.get_by_id(contact_request_id)
        updated = ContactRequest(
            id=contact_request.id,
            name=contact_request.name,
            email_address=contact_request.email_address,
            company=contact_request.company,
            phone=contact_request.phone,
            service=contact_request.service,
            message=contact_request.message,
            status=status,
            created_at=contact_request.created_at,
            updated_at=self._clock(),
            follow_up_at=contact_request.follow_up_at,
        )
        saved = await self._repository.update(updated)
        logger.bind(contact_request_id=str(saved.id), status=status.value).info(
            "Lead status updated"
        )
        return saved

    async def set_follow_up(
        self, contact_request_id: UUID, follow_up_at: datetime | None
    ) -> ContactRequest:
        contact_request = await self.get_by_id(contact_request_id)
        updated = ContactRequest(
            id=contact_request.id,
            name=contact_request.name,
            email_address=contact_request.email_address,
            company=contact_request.company,
            phone=contact_request.phone,
            service=contact_request.service,
            message=contact_request.message,
            status=contact_request.status,
            created_at=contact_request.created_at,
            updated_at=self._clock(),
            follow_up_at=follow_up_at,
        )
        saved = await self._repository.update(updated)
        logger.bind(contact_request_id=str(saved.id)).info("Lead follow-up date updated")
        return saved

    async def list_notes(self, lead_id: UUID) -> list[LeadNote]:
        await self.get_by_id(lead_id)
        return await self._notes.list_for_lead(lead_id)

    async def add_note(self, command: AddLeadNote) -> LeadNote:
        await self.get_by_id(command.lead_id)

        note = LeadNote(
            id=self._id_factory(),
            lead_id=command.lead_id,
            author_id=command.author_id,
            author_name=command.author_name,
            body=command.body,
            created_at=self._clock(),
        )
        saved_note = await self._notes.add(note)
        logger.bind(lead_id=str(command.lead_id)).info("Lead note added")
        return saved_note
