from datetime import UTC, datetime, timedelta
from itertools import count
from uuid import UUID

import pytest

from site_api.domain.scheduling import (
    AppointmentAlreadyCancelledError,
    AppointmentStatus,
    NotAppointmentOwnerError,
    SlotNotAvailableError,
    SlotNotFoundError,
)
from site_api.services.email import EmailService
from site_api.services.scheduling import BookSlot, CreateSlot, SchedulingService
from tests.conftest import FakeSesClient, InMemoryAppointmentRepository

ADMIN_ID = UUID("11111111-1111-1111-1111-111111111111")
CLIENT_ID = UUID("22222222-2222-2222-2222-222222222222")
OTHER_CLIENT_ID = UUID("33333333-3333-3333-3333-333333333333")

NOW = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)


@pytest.fixture
def service(
    appointment_repository: InMemoryAppointmentRepository,
    email_service: EmailService,
) -> SchedulingService:
    ids = iter(UUID(int=n) for n in count(1))
    return SchedulingService(
        appointment_repository,
        email_service,
        id_factory=lambda: next(ids),
        clock=lambda: NOW,
    )


def _create_command(**overrides: object) -> CreateSlot:
    defaults: dict[str, object] = {
        "starts_at": NOW + timedelta(days=1),
        "ends_at": NOW + timedelta(days=1, hours=1),
        "created_by_admin_id": ADMIN_ID,
    }
    defaults.update(overrides)
    return CreateSlot(**defaults)


def _book_command(slot_id: UUID, **overrides: object) -> BookSlot:
    defaults: dict[str, object] = {
        "slot_id": slot_id,
        "client_id": CLIENT_ID,
        "client_name": "Taylor Client",
        "client_email": "taylor@example.com",
        "notes": None,
    }
    defaults.update(overrides)
    return BookSlot(**defaults)


@pytest.mark.asyncio
async def test_create_slot_is_open(service: SchedulingService) -> None:
    slot = await service.create_slot(_create_command())

    assert slot.status is AppointmentStatus.OPEN
    assert slot.client_id is None


@pytest.mark.asyncio
async def test_create_slot_rejects_past_start_time(service: SchedulingService) -> None:
    with pytest.raises(SlotNotAvailableError):
        await service.create_slot(_create_command(starts_at=NOW - timedelta(hours=1)))


@pytest.mark.asyncio
async def test_book_slot_success(service: SchedulingService) -> None:
    slot = await service.create_slot(_create_command())

    booked = await service.book_slot(_book_command(slot.id))

    assert booked.status is AppointmentStatus.BOOKED
    assert booked.client_id == CLIENT_ID
    assert booked.client_name == "Taylor Client"


@pytest.mark.asyncio
async def test_book_slot_raises_when_missing(service: SchedulingService) -> None:
    with pytest.raises(SlotNotFoundError):
        await service.book_slot(_book_command(UUID(int=999)))


@pytest.mark.asyncio
async def test_book_slot_raises_when_already_booked(service: SchedulingService) -> None:
    slot = await service.create_slot(_create_command())
    await service.book_slot(_book_command(slot.id))

    with pytest.raises(SlotNotAvailableError):
        await service.book_slot(_book_command(slot.id, client_id=OTHER_CLIENT_ID))


@pytest.mark.asyncio
async def test_list_open_upcoming_slots_excludes_booked_and_past(
    service: SchedulingService,
) -> None:
    open_slot = await service.create_slot(_create_command())
    booked_slot = await service.create_slot(
        _create_command(starts_at=NOW + timedelta(days=2), ends_at=NOW + timedelta(days=2, hours=1))
    )
    await service.book_slot(_book_command(booked_slot.id))

    open_slots = await service.list_open_upcoming_slots()

    assert [slot.id for slot in open_slots] == [open_slot.id]


@pytest.mark.asyncio
async def test_cancel_own_appointment_success(service: SchedulingService) -> None:
    slot = await service.create_slot(_create_command())
    booked = await service.book_slot(_book_command(slot.id))

    cancelled = await service.cancel_own_appointment(booked.id, CLIENT_ID)

    assert cancelled.status is AppointmentStatus.CANCELLED


@pytest.mark.asyncio
async def test_cancel_own_appointment_rejects_non_owner(service: SchedulingService) -> None:
    slot = await service.create_slot(_create_command())
    booked = await service.book_slot(_book_command(slot.id))

    with pytest.raises(NotAppointmentOwnerError):
        await service.cancel_own_appointment(booked.id, OTHER_CLIENT_ID)


@pytest.mark.asyncio
async def test_cancel_already_cancelled_appointment_raises(service: SchedulingService) -> None:
    slot = await service.create_slot(_create_command())
    booked = await service.book_slot(_book_command(slot.id))
    await service.cancel_own_appointment(booked.id, CLIENT_ID)

    with pytest.raises(AppointmentAlreadyCancelledError):
        await service.cancel_own_appointment(booked.id, CLIENT_ID)


@pytest.mark.asyncio
async def test_admin_cancel_appointment_ignores_ownership(service: SchedulingService) -> None:
    slot = await service.create_slot(_create_command())
    booked = await service.book_slot(_book_command(slot.id))

    cancelled = await service.admin_cancel_appointment(booked.id)

    assert cancelled.status is AppointmentStatus.CANCELLED


@pytest.mark.asyncio
async def test_delete_slot_succeeds_when_open(service: SchedulingService) -> None:
    slot = await service.create_slot(_create_command())

    await service.delete_slot(slot.id)

    assert await service.list_open_upcoming_slots() == []


@pytest.mark.asyncio
async def test_delete_slot_rejects_when_booked(service: SchedulingService) -> None:
    slot = await service.create_slot(_create_command())
    booked = await service.book_slot(_book_command(slot.id))

    with pytest.raises(SlotNotAvailableError):
        await service.delete_slot(booked.id)


@pytest.mark.asyncio
async def test_list_all_appointments_filters_by_status(service: SchedulingService) -> None:
    open_slot = await service.create_slot(_create_command())
    other_slot = await service.create_slot(
        _create_command(starts_at=NOW + timedelta(days=2), ends_at=NOW + timedelta(days=2, hours=1))
    )
    await service.book_slot(_book_command(other_slot.id))

    open_only = await service.list_all_appointments(AppointmentStatus.OPEN)

    assert [slot.id for slot in open_only] == [open_slot.id]


@pytest.mark.asyncio
async def test_list_my_appointments_returns_only_client_bookings(
    service: SchedulingService,
) -> None:
    slot = await service.create_slot(_create_command())
    await service.book_slot(_book_command(slot.id))

    mine = await service.list_my_appointments(CLIENT_ID)
    someone_elses = await service.list_my_appointments(OTHER_CLIENT_ID)

    assert [appointment.id for appointment in mine] == [slot.id]
    assert someone_elses == []


@pytest.mark.asyncio
async def test_book_slot_sends_confirmation_and_admin_emails(
    service: SchedulingService,
    fake_ses_client: FakeSesClient,
) -> None:
    slot = await service.create_slot(_create_command())

    await service.book_slot(_book_command(slot.id))

    assert len(fake_ses_client.sent) == 2
    recipients = {call["Destination"]["ToAddresses"][0] for call in fake_ses_client.sent}
    assert recipients == {"taylor@example.com", "admin@example.com"}
