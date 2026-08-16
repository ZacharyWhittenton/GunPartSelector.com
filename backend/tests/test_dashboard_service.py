from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from site_api.domain.contacts import ContactRequest, ContactRequestStatus
from site_api.domain.marketplace import Order, OrderStatus
from site_api.domain.scheduling import Appointment, AppointmentStatus
from site_api.domain.testimonials import Testimonial, TestimonialStatus
from site_api.services.dashboard import DashboardService
from tests.conftest import (
    InMemoryAppointmentRepository,
    InMemoryContactRequestRepository,
    InMemoryOrderRepository,
    InMemoryTestimonialRepository,
)

NOW = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
ADMIN_ID = UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def service(
    repository: InMemoryContactRequestRepository,
    appointment_repository: InMemoryAppointmentRepository,
    order_repository: InMemoryOrderRepository,
    testimonial_repository: InMemoryTestimonialRepository,
) -> DashboardService:
    return DashboardService(
        repository,
        appointment_repository,
        order_repository,
        testimonial_repository,
        clock=lambda: NOW,
    )


def _make_lead(hours_ago: float, **overrides: object) -> ContactRequest:
    created_at = NOW - timedelta(hours=hours_ago)
    defaults: dict[str, object] = {
        "id": UUID(int=1),
        "name": "Taylor Client",
        "email_address": "taylor@example.com",
        "company": None,
        "phone": None,
        "service": "Website Redesign",
        "message": "Please call me.",
        "status": ContactRequestStatus.RECEIVED,
        "created_at": created_at,
        "updated_at": created_at,
        "follow_up_at": None,
    }
    defaults.update(overrides)
    return ContactRequest(**defaults)


def _make_appointment(starts_delta: timedelta, **overrides: object) -> Appointment:
    defaults: dict[str, object] = {
        "id": UUID(int=100),
        "starts_at": NOW + starts_delta,
        "ends_at": NOW + starts_delta + timedelta(hours=1),
        "status": AppointmentStatus.BOOKED,
        "client_id": UUID(int=200),
        "client_name": "Taylor Client",
        "client_email": "taylor@example.com",
        "notes": None,
        "created_by_admin_id": ADMIN_ID,
        "created_at": NOW,
        "updated_at": NOW,
    }
    defaults.update(overrides)
    return Appointment(**defaults)


def _make_order(days_ago: float, **overrides: object) -> Order:
    created_at = NOW - timedelta(days=days_ago)
    defaults: dict[str, object] = {
        "id": UUID(int=300),
        "stripe_checkout_session_id": f"cs_{days_ago}",
        "stripe_payment_intent_id": "pi_test",
        "customer_id": None,
        "customer_email": "guest@example.com",
        "status": OrderStatus.PAID,
        "total_cents": 5000,
        "discount_code": None,
        "discount_cents": 0,
        "created_at": created_at,
        "updated_at": created_at,
    }
    defaults.update(overrides)
    return Order(**defaults)


def _make_testimonial(**overrides: object) -> Testimonial:
    defaults: dict[str, object] = {
        "id": UUID(int=400),
        "customer_id": None,
        "customer_name": "Priya Anand",
        "rating": 5,
        "body": "Great work.",
        "status": TestimonialStatus.PENDING,
        "created_at": NOW,
        "updated_at": NOW,
    }
    defaults.update(overrides)
    return Testimonial(**defaults)


@pytest.mark.asyncio
async def test_counts_leads_within_today_and_week_windows(
    service: DashboardService,
    repository: InMemoryContactRequestRepository,
) -> None:
    repository.contact_requests.append(_make_lead(2, id=UUID(int=1)))  # today
    repository.contact_requests.append(_make_lead(48, id=UUID(int=2)))  # this week only
    repository.contact_requests.append(_make_lead(24 * 10, id=UUID(int=3)))  # outside window

    summary = await service.get_summary()

    assert summary.new_leads_today == 1
    assert summary.new_leads_this_week == 2


@pytest.mark.asyncio
async def test_upcoming_appointments_excludes_past_and_non_booked(
    service: DashboardService,
    appointment_repository: InMemoryAppointmentRepository,
) -> None:
    appointment_repository.appointments.append(_make_appointment(timedelta(days=1), id=UUID(int=1)))
    appointment_repository.appointments.append(
        _make_appointment(timedelta(days=-1), id=UUID(int=2))
    )
    appointment_repository.appointments.append(
        _make_appointment(timedelta(days=2), id=UUID(int=3), status=AppointmentStatus.OPEN)
    )

    summary = await service.get_summary()

    assert summary.upcoming_appointments == 1


@pytest.mark.asyncio
async def test_revenue_sums_only_paid_orders_within_windows(
    service: DashboardService,
    order_repository: InMemoryOrderRepository,
) -> None:
    order_repository.orders.append(_make_order(2, id=UUID(int=1), total_cents=1000))  # this week
    order_repository.orders.append(_make_order(15, id=UUID(int=2), total_cents=2000))  # this month
    order_repository.orders.append(_make_order(40, id=UUID(int=3), total_cents=4000))  # outside
    order_repository.orders.append(
        _make_order(1, id=UUID(int=4), total_cents=8000, status=OrderStatus.OPEN)
    )

    summary = await service.get_summary()

    assert summary.revenue_this_week_cents == 1000
    assert summary.revenue_this_month_cents == 3000


@pytest.mark.asyncio
async def test_pending_testimonials_counts_only_pending(
    service: DashboardService,
    testimonial_repository: InMemoryTestimonialRepository,
) -> None:
    testimonial_repository.testimonials.append(_make_testimonial(id=UUID(int=1)))
    testimonial_repository.testimonials.append(
        _make_testimonial(id=UUID(int=2), status=TestimonialStatus.APPROVED)
    )

    summary = await service.get_summary()

    assert summary.pending_testimonials == 1


@pytest.mark.asyncio
async def test_recent_activity_merges_and_sorts_by_recency(
    service: DashboardService,
    repository: InMemoryContactRequestRepository,
    appointment_repository: InMemoryAppointmentRepository,
    order_repository: InMemoryOrderRepository,
) -> None:
    repository.contact_requests.append(_make_lead(3, id=UUID(int=1)))
    appointment_repository.appointments.append(
        _make_appointment(timedelta(days=1), id=UUID(int=2), created_at=NOW - timedelta(hours=1))
    )
    order_repository.orders.append(_make_order(0.05, id=UUID(int=3)))  # ~72 minutes ago

    summary = await service.get_summary()

    types_in_order = [item.activity_type for item in summary.recent_activity]
    assert types_in_order == ["appointment", "order", "lead"]


@pytest.mark.asyncio
async def test_recent_activity_respects_limit(
    service: DashboardService,
    repository: InMemoryContactRequestRepository,
) -> None:
    for index in range(5):
        repository.contact_requests.append(_make_lead(index, id=UUID(int=index + 1)))

    summary = await service.get_summary(activity_limit=2)

    assert len(summary.recent_activity) == 2


@pytest.mark.asyncio
async def test_leads_needing_follow_up_counts_overdue_open_leads(
    service: DashboardService,
    repository: InMemoryContactRequestRepository,
) -> None:
    repository.contact_requests.append(
        _make_lead(3, id=UUID(int=1), follow_up_at=NOW - timedelta(hours=1))
    )  # overdue
    repository.contact_requests.append(
        _make_lead(3, id=UUID(int=2), follow_up_at=NOW + timedelta(days=1))
    )  # not due yet
    repository.contact_requests.append(_make_lead(3, id=UUID(int=3), follow_up_at=None))  # unset
    repository.contact_requests.append(
        _make_lead(
            3,
            id=UUID(int=4),
            follow_up_at=NOW - timedelta(hours=1),
            status=ContactRequestStatus.WON,
        )
    )  # closed, excluded

    summary = await service.get_summary()

    assert summary.leads_needing_follow_up == 1
