from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from site_api.db.models import DiscountCodeRecord
from site_api.db.repositories import SqlAlchemyDiscountCodeRepository
from site_api.domain.discount_codes import (
    DiscountCode,
    DiscountCodeNotFoundError,
    DiscountType,
)

CODE_ID = UUID("9a53d09a-f258-4b09-9fb3-ef6df4c2f9fd")
CREATED_AT = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
UPDATED_AT = datetime(2026, 8, 10, 13, 0, tzinfo=UTC)


class FakeSession:
    def __init__(
        self,
        records: dict[UUID, object] | None = None,
        query_result: object = None,
    ) -> None:
        self.added: list[object] = []
        self.deleted: list[object] = []
        self.flushed = False
        self._records = records or {}
        self._query_result = query_result

    def add(self, record: object) -> None:
        self.added.append(record)

    async def flush(self) -> None:
        self.flushed = True

    async def delete(self, record: object) -> None:
        self.deleted.append(record)

    async def get(self, _model_cls: object, pk: UUID) -> object | None:
        return self._records.get(pk)

    async def execute(self, _statement: object) -> _Result:
        return _Result(self._query_result)


class _Result:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object | None:
        return self._value

    def scalars(self) -> _Scalars:
        return _Scalars(self._value if isinstance(self._value, list) else [])


class _Scalars:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def all(self) -> list[object]:
        return self._values


def _make_code(**overrides: object) -> DiscountCode:
    defaults: dict[str, object] = {
        "id": CODE_ID,
        "code": "SAVE10",
        "discount_type": DiscountType.PERCENT,
        "value": 10,
        "is_active": True,
        "expires_at": None,
        "max_redemptions": None,
        "redemption_count": 0,
        "created_at": CREATED_AT,
        "updated_at": CREATED_AT,
    }
    defaults.update(overrides)
    return DiscountCode(**defaults)


def _make_code_record(**overrides: object) -> DiscountCodeRecord:
    defaults: dict[str, object] = {
        "id": CODE_ID,
        "code": "SAVE10",
        "discount_type": "percent",
        "value": 10,
        "is_active": True,
        "expires_at": None,
        "max_redemptions": None,
        "redemption_count": 0,
        "created_at": CREATED_AT,
        "updated_at": CREATED_AT,
    }
    defaults.update(overrides)
    return DiscountCodeRecord(**defaults)


@pytest.mark.asyncio
async def test_add_maps_and_flushes() -> None:
    session = FakeSession()
    repository = SqlAlchemyDiscountCodeRepository(cast(AsyncSession, session))
    code = _make_code()

    result = await repository.add(code)

    assert result is code
    assert session.flushed is True
    record = session.added[0]
    assert isinstance(record, DiscountCodeRecord)
    assert record.code == "SAVE10"
    assert record.discount_type == "percent"


@pytest.mark.asyncio
async def test_update_mutates_record() -> None:
    record = _make_code_record()
    session = FakeSession(records={CODE_ID: record})
    repository = SqlAlchemyDiscountCodeRepository(cast(AsyncSession, session))
    updated = _make_code(
        discount_type=DiscountType.FIXED,
        value=500,
        redemption_count=3,
        updated_at=UPDATED_AT,
    )

    result = await repository.update(updated)

    assert result.discount_type is DiscountType.FIXED
    assert record.discount_type == "fixed"
    assert record.value == 500
    assert record.redemption_count == 3
    assert record.updated_at == UPDATED_AT


@pytest.mark.asyncio
async def test_update_raises_when_missing() -> None:
    session = FakeSession()
    repository = SqlAlchemyDiscountCodeRepository(cast(AsyncSession, session))

    with pytest.raises(DiscountCodeNotFoundError):
        await repository.update(_make_code())


@pytest.mark.asyncio
async def test_delete_removes_record() -> None:
    record = _make_code_record()
    session = FakeSession(records={CODE_ID: record})
    repository = SqlAlchemyDiscountCodeRepository(cast(AsyncSession, session))

    await repository.delete(CODE_ID)

    assert session.deleted == [record]


@pytest.mark.asyncio
async def test_delete_raises_when_missing() -> None:
    session = FakeSession()
    repository = SqlAlchemyDiscountCodeRepository(cast(AsyncSession, session))

    with pytest.raises(DiscountCodeNotFoundError):
        await repository.delete(CODE_ID)


@pytest.mark.asyncio
async def test_get_by_id_maps_record() -> None:
    record = _make_code_record()
    session = FakeSession(records={CODE_ID: record})
    repository = SqlAlchemyDiscountCodeRepository(cast(AsyncSession, session))

    code = await repository.get_by_id(CODE_ID)

    assert code is not None
    assert code.code == "SAVE10"


@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_missing() -> None:
    session = FakeSession()
    repository = SqlAlchemyDiscountCodeRepository(cast(AsyncSession, session))

    assert await repository.get_by_id(CODE_ID) is None


@pytest.mark.asyncio
async def test_get_by_code_maps_record() -> None:
    record = _make_code_record()
    session = FakeSession(query_result=record)
    repository = SqlAlchemyDiscountCodeRepository(cast(AsyncSession, session))

    code = await repository.get_by_code("SAVE10")

    assert code is not None
    assert code.id == CODE_ID


@pytest.mark.asyncio
async def test_get_by_code_returns_none_when_missing() -> None:
    session = FakeSession(query_result=None)
    repository = SqlAlchemyDiscountCodeRepository(cast(AsyncSession, session))

    assert await repository.get_by_code("MISSING") is None


@pytest.mark.asyncio
async def test_list_all_maps_every_record() -> None:
    first = _make_code_record()
    second = _make_code_record(id=UUID(int=2), code="OTHER")
    session = FakeSession(query_result=[first, second])
    repository = SqlAlchemyDiscountCodeRepository(cast(AsyncSession, session))

    codes = await repository.list_all()

    assert [code.id for code in codes] == [first.id, second.id]
