import asyncio
from datetime import datetime
from typing import Any

from loguru import logger

from site_api.domain.contacts import ContactRequest
from site_api.domain.marketplace import Order, OrderItem
from site_api.domain.scheduling import Appointment


class EmailService:
    def __init__(
        self,
        ses_client: Any | None,
        sender_address: str | None,
        admin_email: str | None,
    ) -> None:
        self._client = ses_client
        self._sender = sender_address
        self._admin_email = admin_email

    @property
    def is_configured(self) -> bool:
        return self._client is not None and self._sender is not None

    async def notify_admin_new_lead(self, lead: ContactRequest) -> None:
        if self._admin_email is None:
            return

        subject = f"New lead: {lead.name} ({lead.service})"
        body = (
            "New contact form submission.\n\n"
            f"Name: {lead.name}\n"
            f"Email: {lead.email_address}\n"
            f"Phone: {lead.phone or 'n/a'}\n"
            f"Company: {lead.company or 'n/a'}\n"
            f"Service: {lead.service}\n\n"
            f"Message:\n{lead.message}\n"
        )
        await self._send(self._admin_email, subject, body)

    async def send_appointment_confirmation(self, appointment: Appointment) -> None:
        if appointment.client_email is None:
            return

        subject = "Your appointment is confirmed"
        body = (
            f"Hi {appointment.client_name or 'there'},\n\n"
            "Your appointment is confirmed for "
            f"{_format_datetime(appointment.starts_at)}.\n\n"
            "If you need to reschedule or cancel, just reply to this email.\n"
        )
        await self._send(appointment.client_email, subject, body)

    async def notify_admin_new_appointment(self, appointment: Appointment) -> None:
        if self._admin_email is None:
            return

        subject = f"New booking: {appointment.client_name or 'a client'}"
        body = (
            "A new appointment was booked.\n\n"
            f"Client: {appointment.client_name or 'n/a'}\n"
            f"Email: {appointment.client_email or 'n/a'}\n"
            f"When: {_format_datetime(appointment.starts_at)}\n"
            f"Notes: {appointment.notes or 'none'}\n"
        )
        await self._send(self._admin_email, subject, body)

    async def send_order_confirmation(self, order: Order, items: list[OrderItem]) -> None:
        if order.customer_email is None:
            return

        subject = "Your order is confirmed"
        body = (
            "Thanks for your order!\n\n"
            f"{_format_order_lines(items)}\n\n"
            f"Total: {_format_cents(order.total_cents)}\n"
        )
        await self._send(order.customer_email, subject, body)

    async def notify_admin_new_order(self, order: Order, items: list[OrderItem]) -> None:
        if self._admin_email is None:
            return

        subject = f"New paid order ({_format_cents(order.total_cents)})"
        body = (
            "A new order was paid.\n\n"
            f"Customer: {order.customer_email or 'guest'}\n\n"
            f"{_format_order_lines(items)}\n\n"
            f"Total: {_format_cents(order.total_cents)}\n"
        )
        await self._send(self._admin_email, subject, body)

    async def _send(self, to: str, subject: str, body: str) -> None:
        if not self.is_configured:
            logger.bind(to=to, subject=subject).info("Email not configured, skipping send")
            return

        try:
            await asyncio.to_thread(
                self._client.send_email,
                Source=self._sender,
                Destination={"ToAddresses": [to]},
                Message={
                    "Subject": {"Data": subject},
                    "Body": {"Text": {"Data": body}},
                },
            )
        except Exception:
            logger.bind(to=to, subject=subject).exception("Failed to send email")


def _format_datetime(value: datetime) -> str:
    return value.strftime("%A, %B %d, %Y at %I:%M %p %Z")


def _format_cents(cents: int) -> str:
    return f"${cents / 100:.2f}"


def _format_order_lines(items: list[OrderItem]) -> str:
    return "\n".join(
        f"  - {item.item_name} x{item.quantity}: {_format_cents(item.line_total_cents)}"
        for item in items
    )
