from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from site_api.domain.contacts import ContactRequest, ContactRequestRepository, ContactRequestStatus
from site_api.domain.marketplace import Order, OrderRepository, OrderStatus
from site_api.domain.scheduling import Appointment, AppointmentRepository, AppointmentStatus
from site_api.domain.testimonials import TestimonialRepository, TestimonialStatus

DEFAULT_ACTIVITY_LIMIT = 10
_CLOSED_LEAD_STATUSES = frozenset({ContactRequestStatus.WON, ContactRequestStatus.LOST})


@dataclass(frozen=True, slots=True)
class ActivityItem:
    activity_type: str
    id: UUID
    label: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class DashboardSummary:
    new_leads_today: int
    new_leads_this_week: int
    upcoming_appointments: int
    revenue_this_week_cents: int
    revenue_this_month_cents: int
    pending_testimonials: int
    leads_needing_follow_up: int
    recent_activity: list[ActivityItem]


class DashboardService:
    def __init__(
        self,
        contact_repository: ContactRequestRepository,
        appointment_repository: AppointmentRepository,
        order_repository: OrderRepository,
        testimonial_repository: TestimonialRepository,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._contacts = contact_repository
        self._appointments = appointment_repository
        self._orders = order_repository
        self._testimonials = testimonial_repository
        self._clock = clock

    async def get_summary(self, activity_limit: int = DEFAULT_ACTIVITY_LIMIT) -> DashboardSummary:
        now = self._clock()
        today_cutoff = now - timedelta(days=1)
        week_cutoff = now - timedelta(days=7)
        month_cutoff = now - timedelta(days=30)

        leads = await self._contacts.list_all()
        booked_appointments = await self._appointments.list_all(AppointmentStatus.BOOKED)
        paid_orders = await self._orders.list_all(OrderStatus.PAID)
        pending_testimonials = await self._testimonials.list_all(TestimonialStatus.PENDING)

        new_leads_today = sum(1 for lead in leads if lead.created_at >= today_cutoff)
        new_leads_this_week = sum(1 for lead in leads if lead.created_at >= week_cutoff)
        upcoming_appointments = sum(
            1 for appointment in booked_appointments if appointment.starts_at >= now
        )
        # Orders don't currently track a reliable "paid at" timestamp, so recency is
        # approximated from when the checkout session was created (payment normally
        # follows within minutes, well inside these day-wide windows).
        revenue_this_week_cents = sum(
            order.total_cents for order in paid_orders if order.created_at >= week_cutoff
        )
        revenue_this_month_cents = sum(
            order.total_cents for order in paid_orders if order.created_at >= month_cutoff
        )
        leads_needing_follow_up = sum(
            1
            for lead in leads
            if lead.follow_up_at is not None
            and lead.follow_up_at <= now
            and lead.status not in _CLOSED_LEAD_STATUSES
        )

        activity = _build_activity(leads, booked_appointments, paid_orders)

        return DashboardSummary(
            new_leads_today=new_leads_today,
            new_leads_this_week=new_leads_this_week,
            upcoming_appointments=upcoming_appointments,
            revenue_this_week_cents=revenue_this_week_cents,
            revenue_this_month_cents=revenue_this_month_cents,
            pending_testimonials=len(pending_testimonials),
            leads_needing_follow_up=leads_needing_follow_up,
            recent_activity=activity[:activity_limit],
        )


def _build_activity(
    leads: list[ContactRequest],
    appointments: list[Appointment],
    orders: list[Order],
) -> list[ActivityItem]:
    activity = [
        ActivityItem(
            activity_type="lead",
            id=lead.id,
            label=f"New lead: {lead.name} ({lead.service})",
            occurred_at=lead.created_at,
        )
        for lead in leads
    ]
    activity += [
        ActivityItem(
            activity_type="appointment",
            id=appointment.id,
            label=(
                f"Booking: {appointment.client_name or 'a client'} — "
                f"{appointment.starts_at.strftime('%b %d, %Y %I:%M %p')}"
            ),
            occurred_at=appointment.created_at,
        )
        for appointment in appointments
    ]
    activity += [
        ActivityItem(
            activity_type="order",
            id=order.id,
            label=f"Order paid: ${order.total_cents / 100:.2f}",
            occurred_at=order.created_at,
        )
        for order in orders
    ]
    activity.sort(key=lambda item: item.occurred_at, reverse=True)
    return activity
