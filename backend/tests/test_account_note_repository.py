from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from site_api.db.models import AccountNoteRecord
from site_api.db.repositories import SqlAlchemyAccountNoteRepository
from site_api.domain.account_notes import AccountNote


class RecordingSession:
    def __init__(self, query_result: list[object] | None = None) -> None:
        self.added: list[object] = []
        self.flushed = False
        self._query_result = query_result or []

    def add(self, record: object) -> None:
        self.added.append(record)

    async def flush(self) -> None:
        self.flushed = True

    async def execute(self, _statement: object) -> _ScalarsWrapper:
        return _ScalarsWrapper(self._query_result)


class _ScalarsWrapper:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def scalars(self) -> _ScalarsResult:
        return _ScalarsResult(self._values)


class _ScalarsResult:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def all(self) -> list[object]:
        return self._values


@pytest.mark.asyncio
async def test_repository_maps_and_flushes_note() -> None:
    session = RecordingSession()
    repository = SqlAlchemyAccountNoteRepository(cast(AsyncSession, session))
    note = AccountNote(
        id=UUID("9a53d09a-f258-4b09-9fb3-ef6df4c2f9fd"),
        user_id=UUID("11111111-1111-1111-1111-111111111111"),
        author_id=UUID("22222222-2222-2222-2222-222222222222"),
        author_name="Admin Person",
        body="Called about a quote.",
        created_at=datetime(2026, 8, 8, 12, 0, tzinfo=UTC),
    )

    result = await repository.add(note)

    assert result is note
    assert session.flushed is True
    record = session.added[0]
    assert isinstance(record, AccountNoteRecord)
    assert record.body == note.body
    assert record.author_name == note.author_name


@pytest.mark.asyncio
async def test_list_for_user_maps_records() -> None:
    user_id = UUID("11111111-1111-1111-1111-111111111111")
    record = AccountNoteRecord(
        id=UUID("9a53d09a-f258-4b09-9fb3-ef6df4c2f9fd"),
        user_id=user_id,
        author_id=UUID("22222222-2222-2222-2222-222222222222"),
        author_name="Admin Person",
        body="Called about a quote.",
        created_at=datetime(2026, 8, 8, 12, 0, tzinfo=UTC),
    )
    session = RecordingSession(query_result=[record])
    repository = SqlAlchemyAccountNoteRepository(cast(AsyncSession, session))

    notes = await repository.list_for_user(user_id)

    assert len(notes) == 1
    assert notes[0].id == record.id
    assert notes[0].body == record.body
