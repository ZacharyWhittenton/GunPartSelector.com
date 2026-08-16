from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from site_api.db.models import LeadNoteRecord
from site_api.db.repositories import SqlAlchemyLeadNoteRepository
from site_api.domain.lead_notes import LeadNote

LEAD_ID = UUID("11111111-1111-1111-1111-111111111111")
AUTHOR_ID = UUID("22222222-2222-2222-2222-222222222222")
CREATED_AT = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)


class FakeSession:
    def __init__(self, query_result: object = None) -> None:
        self.added: list[object] = []
        self.flushed = False
        self._query_result = query_result

    def add(self, record: object) -> None:
        self.added.append(record)

    async def flush(self) -> None:
        self.flushed = True

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


def _make_note(**overrides: object) -> LeadNote:
    defaults: dict[str, object] = {
        "id": UUID(int=1),
        "lead_id": LEAD_ID,
        "author_id": AUTHOR_ID,
        "author_name": "Admin Person",
        "body": "Called, left a voicemail.",
        "created_at": CREATED_AT,
    }
    defaults.update(overrides)
    return LeadNote(**defaults)


def _make_note_record(**overrides: object) -> LeadNoteRecord:
    defaults: dict[str, object] = {
        "id": UUID(int=1),
        "lead_id": LEAD_ID,
        "author_id": AUTHOR_ID,
        "author_name": "Admin Person",
        "body": "Called, left a voicemail.",
        "created_at": CREATED_AT,
    }
    defaults.update(overrides)
    return LeadNoteRecord(**defaults)


@pytest.mark.asyncio
async def test_add_note_maps_and_flushes() -> None:
    session = FakeSession()
    repository = SqlAlchemyLeadNoteRepository(cast(AsyncSession, session))
    note = _make_note()

    result = await repository.add(note)

    assert result is note
    assert session.flushed is True
    record = session.added[0]
    assert isinstance(record, LeadNoteRecord)
    assert record.body == note.body
    assert record.lead_id == LEAD_ID


@pytest.mark.asyncio
async def test_list_for_lead_maps_every_record() -> None:
    first = _make_note_record()
    second = _make_note_record(id=UUID(int=2), body="Second note")
    session = FakeSession(query_result=[first, second])
    repository = SqlAlchemyLeadNoteRepository(cast(AsyncSession, session))

    notes = await repository.list_for_lead(LEAD_ID)

    assert [note.id for note in notes] == [first.id, second.id]
    assert notes[0].author_name == "Admin Person"
