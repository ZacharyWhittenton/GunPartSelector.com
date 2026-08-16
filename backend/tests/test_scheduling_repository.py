from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from site_api.db.models import AppointmentRecord
from site_api.db.repositories import SqlAlchemyAppointmentRepository
from site_api.domain.scheduling import Appointment, AppointmentStatus, SlotNotFoundError

APPOINTMENT_ID = UUID("9a53d09a-f258-4b09-9fb3-ef6df4c2f9fd")
ADMIN_ID = UUID("11111111-1111-1111-1111-111111111111")
CLIENT_ID = UUID("22222222-2222-2222-2222-222222222222")
CREATED_AT = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)


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

    async def execute(self, _statement: object) -> "_Result":
        return _Result(self._query_result)


class _Result:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object | None:
        return self._value

    def scalars(self) -> "_Scalars":
        return _Scalars(self._value if isinstance(self._value, list) else [])


class _Scalars:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def all(self) -> list[object]:
        return self._values


def _make_appointment(**overrides: object) -> Appointment:
    defaults: dict[str, object] = {
        "id": APPOINTMENT_ID,
        "starts_at": CREATED_AT,
        "ends_at": CREATED_AT,
        "status": AppointmentStatus.OPEN,
        "client_id": None,
        "client_name": None,
        "client_email": None,
        "notes": None,
        "created_by_admin_id": ADMIN_ID,
        "created_at": CREATED_AT,
        "updated_at": CREATED_AT,
    }
    defaults.update(overrides)
    return Appointment(**defaults)


def _make_appointment_record(**overrides: object) -> AppointmentRecord:
    defaults: dict[str, object] = {
        "id": APPOINTMENT_ID,
        "starts_at": CREATED_AT,
        "ends_at": CREATED_AT,
        "status": "open",
        "client_id": None,
        "client_name": None,
        "client_email": None,
        "notes": None,
        "created_by_admin_id": ADMIN_ID,
        "created_at": CREATED_AT,
        "updated_at": CREATED_AT,
    }
    defaults.update(overrides)
    return AppointmentRecord(**defaults)


@pytest.mark.asyncio
async def test_add_appointment_maps_and_flushes() -> None:
    session = FakeSession()
    repository = SqlAlchemyAppointmentRepository(cast(AsyncSession, session))
    appointment = _make_appointment()

    result = await repository.add(appointment)

    assert result is appointment
    assert session.flushed is True
    record = session.added[0]
    assert isinstance(record, AppointmentRecord)
    assert record.status == "open"


@pytest.mark.asyncio
async def test_update_appointment_mutates_record() -> None:
    record = _make_appointment_record()
    session = FakeSession(records={APPOINTMENT_ID: record})
    repository = SqlAlchemyAppointmentRepository(cast(AsyncSession, session))
    updated = _make_appointment(status=AppointmentStatus.BOOKED, client_id=CLIENT_ID)

    result = await repository.update(updated)

    assert result.status is AppointmentStatus.BOOKED
    assert record.status == "booked"
    assert record.client_id == CLIENT_ID


@pytest.mark.asyncio
async def test_update_appointment_raises_when_missing() -> None:
    session = FakeSession()
    repository = SqlAlchemyAppointmentRepository(cast(AsyncSession, session))

    with pytest.raises(SlotNotFoundError):
        await repository.update(_make_appointment())


@pytest.mark.asyncio
async def test_delete_appointment_removes_record() -> None:
    record = _make_appointment_record()
    session = FakeSession(records={APPOINTMENT_ID: record})
    repository = SqlAlchemyAppointmentRepository(cast(AsyncSession, session))

    await repository.delete(APPOINTMENT_ID)

    assert session.deleted == [record]


@pytest.mark.asyncio
async def test_delete_appointment_raises_when_missing() -> None:
    session = FakeSession()
    repository = SqlAlchemyAppointmentRepository(cast(AsyncSession, session))

    with pytest.raises(SlotNotFoundError):
        await repository.delete(APPOINTMENT_ID)


@pytest.mark.asyncio
async def test_get_by_id_maps_record() -> None:
    record = _make_appointment_record()
    session = FakeSession(records={APPOINTMENT_ID: record})
    repository = SqlAlchemyAppointmentRepository(cast(AsyncSession, session))

    appointment = await repository.get_by_id(APPOINTMENT_ID)

    assert appointment is not None
    assert appointment.id == record.id


@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_missing() -> None:
    session = FakeSession()
    repository = SqlAlchemyAppointmentRepository(cast(AsyncSession, session))

    assert await repository.get_by_id(APPOINTMENT_ID) is None


@pytest.mark.asyncio
async def test_list_open_upcoming_maps_every_record() -> None:
    first = _make_appointment_record()
    second = _make_appointment_record(id=UUID(int=2))
    session = FakeSession(query_result=[first, second])
    repository = SqlAlchemyAppointmentRepository(cast(AsyncSession, session))

    appointments = await repository.list_open_upcoming(CREATED_AT)

    assert [a.id for a in appointments] == [first.id, second.id]


@pytest.mark.asyncio
async def test_list_for_client_maps_records() -> None:
    record = _make_appointment_record(status="booked", client_id=CLIENT_ID)
    session = FakeSession(query_result=[record])
    repository = SqlAlchemyAppointmentRepository(cast(AsyncSession, session))

    appointments = await repository.list_for_client(CLIENT_ID)

    assert len(appointments) == 1
    assert appointments[0].client_id == CLIENT_ID


@pytest.mark.asyncio
async def test_list_all_maps_records() -> None:
    record = _make_appointment_record()
    session = FakeSession(query_result=[record])
    repository = SqlAlchemyAppointmentRepository(cast(AsyncSession, session))

    appointments = await repository.list_all()

    assert len(appointments) == 1
