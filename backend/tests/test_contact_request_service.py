from datetime import UTC, datetime
from itertools import count
from uuid import UUID

import pytest

from site_api.domain.contacts import ContactRequestNotFoundError, ContactRequestStatus
from site_api.services.contact_requests import (
    AddLeadNote,
    ContactRequestService,
    SubmitContactRequest,
)
from site_api.services.email import EmailService
from tests.conftest import (
    FakeSesClient,
    InMemoryContactRequestRepository,
    InMemoryLeadNoteRepository,
)


@pytest.mark.asyncio
async def test_submit_builds_and_persists_contact_request(
    repository: InMemoryContactRequestRepository,
    lead_note_repository: InMemoryLeadNoteRepository,
) -> None:
    expected_id = UUID("9a53d09a-f258-4b09-9fb3-ef6df4c2f9fd")
    expected_time = datetime(2026, 8, 4, 12, 0, tzinfo=UTC)
    service = ContactRequestService(
        repository,
        lead_note_repository,
        id_factory=lambda: expected_id,
        clock=lambda: expected_time,
    )

    result = await service.submit(
        SubmitContactRequest(
            name="Taylor Client",
            email_address="taylor@example.com",
            company=None,
            phone=None,
            service="Asphalt Repair",
            message="Please call me.",
        )
    )

    assert result.id == expected_id
    assert result.created_at == expected_time
    assert result.updated_at == expected_time
    assert result.status is ContactRequestStatus.RECEIVED
    assert repository.contact_requests == [result]


def _submit_command(**overrides: object) -> SubmitContactRequest:
    defaults: dict[str, object] = {
        "name": "Taylor Client",
        "email_address": "taylor@example.com",
        "company": None,
        "phone": None,
        "service": "Website Redesign",
        "message": "Please call me.",
    }
    defaults.update(overrides)
    return SubmitContactRequest(**defaults)


@pytest.fixture
def service(
    repository: InMemoryContactRequestRepository,
    lead_note_repository: InMemoryLeadNoteRepository,
    email_service: EmailService,
) -> ContactRequestService:
    ids = iter(UUID(int=n) for n in count(1))
    return ContactRequestService(
        repository, lead_note_repository, email_service, id_factory=lambda: next(ids)
    )


@pytest.mark.asyncio
async def test_list_all_filters_by_status(service: ContactRequestService) -> None:
    first = await service.submit(_submit_command())
    second = await service.submit(_submit_command(email_address="other@example.com"))
    await service.update_status(second.id, ContactRequestStatus.CONTACTED)

    received_only = await service.list_all(ContactRequestStatus.RECEIVED)
    contacted_only = await service.list_all(ContactRequestStatus.CONTACTED)

    assert [lead.id for lead in received_only] == [first.id]
    assert [lead.id for lead in contacted_only] == [second.id]


@pytest.mark.asyncio
async def test_get_by_id_raises_when_missing(service: ContactRequestService) -> None:
    with pytest.raises(ContactRequestNotFoundError):
        await service.get_by_id(UUID(int=999))


@pytest.mark.asyncio
async def test_update_status_moves_lead_through_pipeline(
    service: ContactRequestService,
) -> None:
    lead = await service.submit(_submit_command())

    contacted = await service.update_status(lead.id, ContactRequestStatus.CONTACTED)
    assert contacted.status is ContactRequestStatus.CONTACTED
    assert contacted.updated_at >= lead.created_at

    won = await service.update_status(lead.id, ContactRequestStatus.WON)
    assert won.status is ContactRequestStatus.WON
    assert won.created_at == lead.created_at


@pytest.mark.asyncio
async def test_update_status_raises_when_missing(service: ContactRequestService) -> None:
    with pytest.raises(ContactRequestNotFoundError):
        await service.update_status(UUID(int=999), ContactRequestStatus.LOST)


@pytest.mark.asyncio
async def test_submit_notifies_admin_by_email(
    service: ContactRequestService,
    fake_ses_client: FakeSesClient,
) -> None:
    await service.submit(_submit_command())

    assert len(fake_ses_client.sent) == 1
    assert fake_ses_client.sent[0]["Destination"] == {"ToAddresses": ["admin@example.com"]}


@pytest.mark.asyncio
async def test_add_note_persists_and_lists_for_lead(service: ContactRequestService) -> None:
    lead = await service.submit(_submit_command())

    note = await service.add_note(
        AddLeadNote(
            lead_id=lead.id,
            author_id=UUID(int=500),
            author_name="Admin Person",
            body="Called, left a voicemail.",
        )
    )

    assert note.lead_id == lead.id
    assert note.author_name == "Admin Person"

    notes = await service.list_notes(lead.id)
    assert [item.id for item in notes] == [note.id]


@pytest.mark.asyncio
async def test_add_note_raises_when_lead_missing(service: ContactRequestService) -> None:
    with pytest.raises(ContactRequestNotFoundError):
        await service.add_note(
            AddLeadNote(
                lead_id=UUID(int=999),
                author_id=UUID(int=500),
                author_name="Admin Person",
                body="Note body",
            )
        )


@pytest.mark.asyncio
async def test_list_notes_raises_when_lead_missing(service: ContactRequestService) -> None:
    with pytest.raises(ContactRequestNotFoundError):
        await service.list_notes(UUID(int=999))


@pytest.mark.asyncio
async def test_set_follow_up_persists_date(service: ContactRequestService) -> None:
    lead = await service.submit(_submit_command())
    follow_up_at = datetime(2026, 8, 15, 9, 0, tzinfo=UTC)

    updated = await service.set_follow_up(lead.id, follow_up_at)

    assert updated.follow_up_at == follow_up_at
    assert updated.status == lead.status


@pytest.mark.asyncio
async def test_set_follow_up_clears_date(service: ContactRequestService) -> None:
    lead = await service.submit(_submit_command())
    await service.set_follow_up(lead.id, datetime(2026, 8, 15, 9, 0, tzinfo=UTC))

    cleared = await service.set_follow_up(lead.id, None)

    assert cleared.follow_up_at is None


@pytest.mark.asyncio
async def test_set_follow_up_raises_when_lead_missing(service: ContactRequestService) -> None:
    with pytest.raises(ContactRequestNotFoundError):
        await service.set_follow_up(UUID(int=999), datetime(2026, 8, 15, 9, 0, tzinfo=UTC))
