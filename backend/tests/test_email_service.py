from datetime import UTC, datetime
from uuid import UUID

import pytest

from site_api.domain.contacts import ContactRequest, ContactRequestStatus
from site_api.domain.marketplace import Order, OrderItem, OrderStatus
from site_api.domain.scheduling import Appointment, AppointmentStatus
from site_api.services.email import EmailService
from tests.conftest import FakeSesClient

NOW = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)


def _make_lead(**overrides: object) -> ContactRequest:
    defaults: dict[str, object] = {
        "id": UUID(int=1),
        "name": "Taylor Client",
        "email_address": "taylor@example.com",
        "company": None,
        "phone": None,
        "service": "Website Redesign",
        "message": "Please call me.",
        "status": ContactRequestStatus.RECEIVED,
        "created_at": NOW,
        "updated_at": NOW,
        "follow_up_at": None,
    }
    defaults.update(overrides)
    return ContactRequest(**defaults)


def _make_appointment(**overrides: object) -> Appointment:
    defaults: dict[str, object] = {
        "id": UUID(int=1),
        "starts_at": NOW,
        "ends_at": NOW,
        "status": AppointmentStatus.BOOKED,
        "client_id": UUID(int=2),
        "client_name": "Taylor Client",
        "client_email": "taylor@example.com",
        "notes": None,
        "created_by_admin_id": UUID(int=3),
        "created_at": NOW,
        "updated_at": NOW,
    }
    defaults.update(overrides)
    return Appointment(**defaults)


def _make_order(**overrides: object) -> Order:
    defaults: dict[str, object] = {
        "id": UUID(int=1),
        "stripe_checkout_session_id": "cs_test_1",
        "stripe_payment_intent_id": "pi_test_1",
        "customer_id": None,
        "customer_email": "guest@example.com",
        "status": OrderStatus.PAID,
        "total_cents": 5000,
        "discount_code": None,
        "discount_cents": 0,
        "created_at": NOW,
        "updated_at": NOW,
    }
    defaults.update(overrides)
    return Order(**defaults)


def _make_order_items() -> list[OrderItem]:
    return [
        OrderItem(
            id=UUID(int=10),
            order_id=UUID(int=1),
            marketplace_item_id=UUID(int=20),
            item_name="Website Audit",
            unit_price_cents=5000,
            quantity=1,
            line_total_cents=5000,
        )
    ]


@pytest.mark.asyncio
async def test_unconfigured_service_skips_send(fake_ses_client: FakeSesClient) -> None:
    service = EmailService(None, None, "admin@example.com")

    assert service.is_configured is False
    await service.notify_admin_new_lead(_make_lead())

    assert fake_ses_client.sent == []


@pytest.mark.asyncio
async def test_configured_without_admin_email_skips_admin_notifications(
    fake_ses_client: FakeSesClient,
) -> None:
    service = EmailService(fake_ses_client, "sender@example.com", None)

    await service.notify_admin_new_lead(_make_lead())
    await service.notify_admin_new_appointment(_make_appointment())
    await service.notify_admin_new_order(_make_order(), _make_order_items())

    assert fake_ses_client.sent == []


@pytest.mark.asyncio
async def test_notify_admin_new_lead_sends_to_admin(fake_ses_client: FakeSesClient) -> None:
    service = EmailService(fake_ses_client, "sender@example.com", "admin@example.com")

    await service.notify_admin_new_lead(_make_lead())

    assert len(fake_ses_client.sent) == 1
    call = fake_ses_client.sent[0]
    assert call["Source"] == "sender@example.com"
    assert call["Destination"] == {"ToAddresses": ["admin@example.com"]}
    assert "Taylor Client" in call["Message"]["Body"]["Text"]["Data"]


@pytest.mark.asyncio
async def test_send_appointment_confirmation_sends_to_client(
    fake_ses_client: FakeSesClient,
) -> None:
    service = EmailService(fake_ses_client, "sender@example.com", "admin@example.com")

    await service.send_appointment_confirmation(_make_appointment())

    assert len(fake_ses_client.sent) == 1
    assert fake_ses_client.sent[0]["Destination"] == {"ToAddresses": ["taylor@example.com"]}


@pytest.mark.asyncio
async def test_send_appointment_confirmation_skips_when_no_client_email(
    fake_ses_client: FakeSesClient,
) -> None:
    service = EmailService(fake_ses_client, "sender@example.com", "admin@example.com")

    await service.send_appointment_confirmation(_make_appointment(client_email=None))

    assert fake_ses_client.sent == []


@pytest.mark.asyncio
async def test_notify_admin_new_appointment_sends_to_admin(
    fake_ses_client: FakeSesClient,
) -> None:
    service = EmailService(fake_ses_client, "sender@example.com", "admin@example.com")

    await service.notify_admin_new_appointment(_make_appointment())

    assert fake_ses_client.sent[0]["Destination"] == {"ToAddresses": ["admin@example.com"]}


@pytest.mark.asyncio
async def test_send_order_confirmation_sends_to_customer_with_line_items(
    fake_ses_client: FakeSesClient,
) -> None:
    service = EmailService(fake_ses_client, "sender@example.com", "admin@example.com")

    await service.send_order_confirmation(_make_order(), _make_order_items())

    call = fake_ses_client.sent[0]
    assert call["Destination"] == {"ToAddresses": ["guest@example.com"]}
    assert "Website Audit" in call["Message"]["Body"]["Text"]["Data"]
    assert "$50.00" in call["Message"]["Body"]["Text"]["Data"]


@pytest.mark.asyncio
async def test_send_order_confirmation_skips_when_no_customer_email(
    fake_ses_client: FakeSesClient,
) -> None:
    service = EmailService(fake_ses_client, "sender@example.com", "admin@example.com")

    await service.send_order_confirmation(_make_order(customer_email=None), _make_order_items())

    assert fake_ses_client.sent == []


@pytest.mark.asyncio
async def test_notify_admin_new_order_sends_to_admin(fake_ses_client: FakeSesClient) -> None:
    service = EmailService(fake_ses_client, "sender@example.com", "admin@example.com")

    await service.notify_admin_new_order(_make_order(), _make_order_items())

    call = fake_ses_client.sent[0]
    assert call["Destination"] == {"ToAddresses": ["admin@example.com"]}
    assert "$50.00" in call["Message"]["Body"]["Text"]["Data"]


@pytest.mark.asyncio
async def test_send_failure_is_swallowed_not_raised(fake_ses_client: FakeSesClient) -> None:
    fake_ses_client.should_raise = True
    service = EmailService(fake_ses_client, "sender@example.com", "admin@example.com")

    await service.notify_admin_new_lead(_make_lead())
