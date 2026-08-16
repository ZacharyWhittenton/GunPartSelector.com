from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from site_api.db.models import UserRecord
from site_api.db.repositories import SqlAlchemyUserRepository
from site_api.domain.users import AccountStatus, User, UserNotFoundError, UserRole


def _make_record(**overrides: object) -> UserRecord:
    defaults: dict[str, object] = {
        "id": UUID("9a53d09a-f258-4b09-9fb3-ef6df4c2f9fd"),
        "email_address": "taylor@example.com",
        "full_name": "Taylor Client",
        "hashed_password": "hashed-password",
        "role": "customer",
        "status": "active",
        "created_at": datetime(2026, 8, 8, 12, 0, tzinfo=UTC),
        "last_login_at": None,
    }
    defaults.update(overrides)
    return UserRecord(**defaults)


class RecordingSession:
    def __init__(
        self,
        records: dict[UUID, UserRecord] | None = None,
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

    async def get(self, _model_cls: object, pk: UUID) -> UserRecord | None:
        return self._records.get(pk)

    async def execute(self, _statement: object) -> _ScalarResult:
        return _ScalarResult(self._query_result)


class _ScalarResult:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object | None:
        return self._value

    def scalars(self) -> _ScalarsResult:
        return _ScalarsResult(self._value if isinstance(self._value, list) else [])


class _ScalarsResult:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def all(self) -> list[object]:
        return self._values


@pytest.mark.asyncio
async def test_repository_maps_and_flushes_user() -> None:
    session = RecordingSession()
    repository = SqlAlchemyUserRepository(cast(AsyncSession, session))
    user = User(
        id=UUID("9a53d09a-f258-4b09-9fb3-ef6df4c2f9fd"),
        email_address="taylor@example.com",
        full_name="Taylor Client",
        hashed_password="hashed-password",
        role=UserRole.CUSTOMER,
        status=AccountStatus.ACTIVE,
        created_at=datetime(2026, 8, 8, 12, 0, tzinfo=UTC),
        last_login_at=None,
    )

    result = await repository.add(user)

    assert result is user
    assert session.flushed is True
    assert len(session.added) == 1
    record = session.added[0]
    assert isinstance(record, UserRecord)
    assert record.email_address == user.email_address
    assert record.role == user.role.value


@pytest.mark.asyncio
async def test_get_by_email_maps_record_to_domain_user() -> None:
    record = _make_record()
    session = RecordingSession(query_result=record)
    repository = SqlAlchemyUserRepository(cast(AsyncSession, session))

    user = await repository.get_by_email("taylor@example.com")

    assert user is not None
    assert user.id == record.id
    assert user.email_address == record.email_address
    assert user.role is UserRole.CUSTOMER
    assert user.status is AccountStatus.ACTIVE


@pytest.mark.asyncio
async def test_get_by_email_returns_none_when_missing() -> None:
    session = RecordingSession(query_result=None)
    repository = SqlAlchemyUserRepository(cast(AsyncSession, session))

    user = await repository.get_by_email("nobody@example.com")

    assert user is None


@pytest.mark.asyncio
async def test_get_by_id_maps_record_to_domain_user() -> None:
    record = _make_record()
    session = RecordingSession(records={record.id: record})
    repository = SqlAlchemyUserRepository(cast(AsyncSession, session))

    user = await repository.get_by_id(record.id)

    assert user is not None
    assert user.id == record.id


@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_missing() -> None:
    session = RecordingSession()
    repository = SqlAlchemyUserRepository(cast(AsyncSession, session))

    user = await repository.get_by_id(UUID("9a53d09a-f258-4b09-9fb3-ef6df4c2f9fd"))

    assert user is None


@pytest.mark.asyncio
async def test_list_all_maps_every_record() -> None:
    first = _make_record()
    second = _make_record(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        email_address="jordan@example.com",
    )
    session = RecordingSession(query_result=[first, second])
    repository = SqlAlchemyUserRepository(cast(AsyncSession, session))

    users = await repository.list_all()

    assert [user.id for user in users] == [first.id, second.id]


@pytest.mark.asyncio
async def test_update_role_mutates_record_and_returns_domain_user() -> None:
    record = _make_record()
    session = RecordingSession(records={record.id: record})
    repository = SqlAlchemyUserRepository(cast(AsyncSession, session))

    user = await repository.update_role(record.id, UserRole.ADMIN)

    assert user.role is UserRole.ADMIN
    assert record.role == "admin"
    assert session.flushed is True


@pytest.mark.asyncio
async def test_update_role_raises_when_missing() -> None:
    session = RecordingSession()
    repository = SqlAlchemyUserRepository(cast(AsyncSession, session))

    with pytest.raises(UserNotFoundError):
        await repository.update_role(UUID("9a53d09a-f258-4b09-9fb3-ef6df4c2f9fd"), UserRole.ADMIN)


@pytest.mark.asyncio
async def test_update_status_mutates_record_and_returns_domain_user() -> None:
    record = _make_record()
    session = RecordingSession(records={record.id: record})
    repository = SqlAlchemyUserRepository(cast(AsyncSession, session))

    user = await repository.update_status(record.id, AccountStatus.SUSPENDED)

    assert user.status is AccountStatus.SUSPENDED
    assert record.status == "suspended"


@pytest.mark.asyncio
async def test_update_status_raises_when_missing() -> None:
    session = RecordingSession()
    repository = SqlAlchemyUserRepository(cast(AsyncSession, session))

    with pytest.raises(UserNotFoundError):
        await repository.update_status(
            UUID("9a53d09a-f258-4b09-9fb3-ef6df4c2f9fd"), AccountStatus.SUSPENDED
        )


@pytest.mark.asyncio
async def test_update_last_login_sets_timestamp() -> None:
    record = _make_record()
    session = RecordingSession(records={record.id: record})
    repository = SqlAlchemyUserRepository(cast(AsyncSession, session))
    login_time = datetime(2026, 8, 8, 13, 0, tzinfo=UTC)

    await repository.update_last_login(record.id, login_time)

    assert record.last_login_at == login_time


@pytest.mark.asyncio
async def test_update_last_login_raises_when_missing() -> None:
    session = RecordingSession()
    repository = SqlAlchemyUserRepository(cast(AsyncSession, session))

    with pytest.raises(UserNotFoundError):
        await repository.update_last_login(
            UUID("9a53d09a-f258-4b09-9fb3-ef6df4c2f9fd"), datetime(2026, 8, 8, 13, 0, tzinfo=UTC)
        )
