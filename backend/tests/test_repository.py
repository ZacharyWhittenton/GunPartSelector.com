from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from site_api.db.models import ContactRequestRecord
from site_api.db.repositories import SqlAlchemyContactRequestRepository
from site_api.domain.contacts import ContactRequest, ContactRequestStatus


class RecordingSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.flushed = False

    def add(self, record: object) -> None:
        self.added.append(record)

    async def flush(self) -> None:
        self.flushed = True


@pytest.mark.asyncio
async def test_repository_maps_and_flushes_contact_request() -> None:
    session = RecordingSession()
    repository = SqlAlchemyContactRequestRepository(cast(AsyncSession, session))
    contact_request = ContactRequest(
        id=UUID("9a53d09a-f258-4b09-9fb3-ef6df4c2f9fd"),
        name="Taylor Client",
        email_address="taylor@example.com",
        company=None,
        phone=None,
        service="Asphalt Repair",
        message="Please call me.",
        status=ContactRequestStatus.RECEIVED,
        created_at=datetime(2026, 8, 4, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 8, 4, 12, 0, tzinfo=UTC),
        follow_up_at=None,
    )

    result = await repository.add(contact_request)

    assert result is contact_request
    assert session.flushed is True
    assert len(session.added) == 1
    record = session.added[0]
    assert isinstance(record, ContactRequestRecord)
    assert record.email_address == contact_request.email_address
