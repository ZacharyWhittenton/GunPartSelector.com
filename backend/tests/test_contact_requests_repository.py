from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from site_api.db.models import ContactRequestRecord
from site_api.db.repositories import SqlAlchemyContactRequestRepository
from site_api.domain.contacts import (
    ContactRequest,
    ContactRequestNotFoundError,
    ContactRequestStatus,
)

LEAD_ID = UUID("9a53d09a-f258-4b09-9fb3-ef6df4c2f9fd")
CREATED_AT = datetime(2026, 8, 4, 12, 0, tzinfo=UTC)
UPDATED_AT = datetime(2026, 8, 10, 9, 0, tzinfo=UTC)


class FakeSession:
    def __init__(
        self,
        records: dict[UUID, object] | None = None,
        query_result: object = None,
    ) -> None:
        self.added: list[object] = []
        self.flushed = False
        self._records = records or {}
        self._query_result = query_result

    def add(self, record: object) -> None:
        self.added.append(record)

    async def flush(self) -> None:
        self.flushed = True

    async def get(self, _model_cls: object, pk: UUID) -> object | None:
        return self._records.get(pk)

    async def execute(self, _statement: object) -> _Result:
        return _Result(self._query_result)


class _Result:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalars(self) -> _Scalars:
        return _Scalars(self._value if isinstance(self._value, list) else [])


class _Scalars:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def all(self) -> list[object]:
        return self._values


def _make_lead(**overrides: object) -> ContactRequest:
    defaults: dict[str, object] = {
        "id": LEAD_ID,
        "name": "Taylor Client",
        "email_address": "taylor@example.com",
        "company": None,
        "phone": None,
        "service": "Website Redesign",
        "message": "Please call me.",
        "status": ContactRequestStatus.RECEIVED,
        "created_at": CREATED_AT,
        "updated_at": CREATED_AT,
        "follow_up_at": None,
    }
    defaults.update(overrides)
    return ContactRequest(**defaults)


def _make_lead_record(**overrides: object) -> ContactRequestRecord:
    defaults: dict[str, object] = {
        "id": LEAD_ID,
        "name": "Taylor Client",
        "email_address": "taylor@example.com",
        "company": None,
        "phone": None,
        "service": "Website Redesign",
        "message": "Please call me.",
        "status": "received",
        "created_at": CREATED_AT,
        "updated_at": CREATED_AT,
    }
    defaults.update(overrides)
    return ContactRequestRecord(**defaults)


@pytest.mark.asyncio
async def test_update_lead_mutates_record() -> None:
    record = _make_lead_record()
    session = FakeSession(records={LEAD_ID: record})
    repository = SqlAlchemyContactRequestRepository(cast(AsyncSession, session))
    updated = _make_lead(status=ContactRequestStatus.QUALIFIED, updated_at=UPDATED_AT)

    result = await repository.update(updated)

    assert result.status is ContactRequestStatus.QUALIFIED
    assert record.status == "qualified"
    assert record.updated_at == UPDATED_AT


@pytest.mark.asyncio
async def test_update_lead_raises_when_missing() -> None:
    session = FakeSession()
    repository = SqlAlchemyContactRequestRepository(cast(AsyncSession, session))

    with pytest.raises(ContactRequestNotFoundError):
        await repository.update(_make_lead())


@pytest.mark.asyncio
async def test_get_by_id_maps_record() -> None:
    record = _make_lead_record()
    session = FakeSession(records={LEAD_ID: record})
    repository = SqlAlchemyContactRequestRepository(cast(AsyncSession, session))

    lead = await repository.get_by_id(LEAD_ID)

    assert lead is not None
    assert lead.id == record.id
    assert lead.status is ContactRequestStatus.RECEIVED


@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_missing() -> None:
    session = FakeSession()
    repository = SqlAlchemyContactRequestRepository(cast(AsyncSession, session))

    assert await repository.get_by_id(LEAD_ID) is None


@pytest.mark.asyncio
async def test_list_all_maps_every_record() -> None:
    first = _make_lead_record()
    second = _make_lead_record(id=UUID(int=2), status="contacted")
    session = FakeSession(query_result=[first, second])
    repository = SqlAlchemyContactRequestRepository(cast(AsyncSession, session))

    leads = await repository.list_all()

    assert [lead.id for lead in leads] == [first.id, second.id]
