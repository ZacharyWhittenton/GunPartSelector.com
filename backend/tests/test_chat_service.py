from datetime import UTC, datetime
from uuid import UUID

import pytest

from site_api.domain.blog import BlogPost, PostStatus
from site_api.domain.chat import ChatNotConfiguredError, ChatTurn
from site_api.domain.scheduling import Appointment, AppointmentStatus
from site_api.domain.users import AuthenticatedUser, UserRole
from site_api.services.chat import ChatService
from tests.conftest import (
    FakeAnthropicClient,
    InMemoryAppointmentRepository,
    InMemoryBlogPostRepository,
    InMemoryUserRepository,
)

ADMIN_ID = UUID("11111111-1111-1111-1111-111111111111")
CUSTOMER_ID = UUID("22222222-2222-2222-2222-222222222222")


def _published_post() -> BlogPost:
    return BlogPost(
        id=UUID(int=1),
        title="Why Website Maintenance Matters",
        slug="why-website-maintenance-matters",
        excerpt="excerpt",
        body="body",
        cover_image_url=None,
        tags=("maintenance",),
        author_id=ADMIN_ID,
        author_name="Admin",
        status=PostStatus.PUBLISHED,
        published_at=datetime(2026, 1, 1, tzinfo=UTC),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _open_slot() -> Appointment:
    return Appointment(
        id=UUID(int=2),
        starts_at=datetime(2026, 8, 20, tzinfo=UTC),
        ends_at=datetime(2026, 8, 20, 0, 30, tzinfo=UTC),
        status=AppointmentStatus.OPEN,
        client_id=None,
        client_name=None,
        client_email=None,
        notes=None,
        created_by_admin_id=ADMIN_ID,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


@pytest.fixture
def service(
    fake_anthropic_client: FakeAnthropicClient,
    blog_post_repository: InMemoryBlogPostRepository,
    appointment_repository: InMemoryAppointmentRepository,
    user_repository: InMemoryUserRepository,
) -> ChatService:
    return ChatService(
        fake_anthropic_client,  # type: ignore[arg-type]
        blog_post_repository,
        appointment_repository,
        user_repository,
        "claude-opus-5",
    )


@pytest.mark.asyncio
async def test_send_message_without_client_raises(
    blog_post_repository: InMemoryBlogPostRepository,
    appointment_repository: InMemoryAppointmentRepository,
    user_repository: InMemoryUserRepository,
) -> None:
    unconfigured = ChatService(None, blog_post_repository, appointment_repository, user_repository, "claude-opus-5")

    with pytest.raises(ChatNotConfiguredError):
        await unconfigured.send_message([ChatTurn(role="user", content="hi")], None, None)


@pytest.mark.asyncio
async def test_send_message_returns_reply_text(
    service: ChatService, fake_anthropic_client: FakeAnthropicClient
) -> None:
    reply = await service.send_message(
        [ChatTurn(role="user", content="What services do you offer?")], None, None
    )

    assert reply == fake_anthropic_client.messages.reply


@pytest.mark.asyncio
async def test_visitor_system_prompt_mentions_registration(
    service: ChatService, fake_anthropic_client: FakeAnthropicClient
) -> None:
    await service.send_message([ChatTurn(role="user", content="Can I book a call?")], None, None)

    system_prompt = fake_anthropic_client.messages.last_kwargs["system"]
    assert "register" in system_prompt.lower()
    assert "/schedule" in system_prompt


@pytest.mark.asyncio
async def test_customer_system_prompt_includes_own_appointments(
    service: ChatService,
    fake_anthropic_client: FakeAnthropicClient,
    appointment_repository: InMemoryAppointmentRepository,
) -> None:
    booked = Appointment(
        id=UUID(int=3),
        starts_at=datetime(2026, 9, 1, tzinfo=UTC),
        ends_at=datetime(2026, 9, 1, 0, 30, tzinfo=UTC),
        status=AppointmentStatus.BOOKED,
        client_id=CUSTOMER_ID,
        client_name="Taylor Client",
        client_email="taylor@example.com",
        notes=None,
        created_by_admin_id=ADMIN_ID,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    await appointment_repository.add(booked)
    customer = AuthenticatedUser(
        id=CUSTOMER_ID, email_address="taylor@example.com", full_name="Taylor Client", role=UserRole.CUSTOMER
    )

    await service.send_message([ChatTurn(role="user", content="When is my meeting?")], customer, None)

    system_prompt = fake_anthropic_client.messages.last_kwargs["system"]
    assert "Taylor Client" in system_prompt
    assert "2026-09-01" in system_prompt


@pytest.mark.asyncio
async def test_admin_system_prompt_includes_stats(
    service: ChatService,
    fake_anthropic_client: FakeAnthropicClient,
    blog_post_repository: InMemoryBlogPostRepository,
    appointment_repository: InMemoryAppointmentRepository,
) -> None:
    await blog_post_repository.add(_published_post())
    await appointment_repository.add(_open_slot())
    admin = AuthenticatedUser(
        id=ADMIN_ID, email_address="admin@example.com", full_name="Alex Admin", role=UserRole.ADMIN
    )

    await service.send_message([ChatTurn(role="user", content="How many open slots?")], admin, None)

    system_prompt = fake_anthropic_client.messages.last_kwargs["system"]
    assert "Alex Admin" in system_prompt
    assert "1 open" in system_prompt
    assert "Why Website Maintenance Matters" in system_prompt


@pytest.mark.asyncio
async def test_page_context_included_when_provided(
    service: ChatService, fake_anthropic_client: FakeAnthropicClient
) -> None:
    await service.send_message(
        [ChatTurn(role="user", content="What does this page offer?")], None, "Services page"
    )

    system_prompt = fake_anthropic_client.messages.last_kwargs["system"]
    assert "Services page" in system_prompt
