from datetime import UTC, datetime
from uuid import UUID

import pytest

from site_api.domain.blog import BlogPost, PostStatus
from site_api.domain.chat import ChatNotConfiguredError, ChatTurn
from site_api.domain.users import AuthenticatedUser, UserRole
from site_api.services.chat import ChatService
from tests.conftest import FakeAnthropicClient, InMemoryBlogPostRepository, InMemoryUserRepository

ADMIN_ID = UUID("11111111-1111-1111-1111-111111111111")
CUSTOMER_ID = UUID("22222222-2222-2222-2222-222222222222")


def _published_post() -> BlogPost:
    return BlogPost(
        id=UUID(int=1),
        title="Choosing a Barrel Length",
        slug="choosing-a-barrel-length",
        excerpt="excerpt",
        body="body",
        cover_image_url=None,
        tags=("barrel",),
        author_id=ADMIN_ID,
        author_name="Admin",
        status=PostStatus.PUBLISHED,
        published_at=datetime(2026, 1, 1, tzinfo=UTC),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


@pytest.fixture
def service(
    fake_anthropic_client: FakeAnthropicClient,
    blog_post_repository: InMemoryBlogPostRepository,
    user_repository: InMemoryUserRepository,
) -> ChatService:
    return ChatService(
        fake_anthropic_client,  # type: ignore[arg-type]
        blog_post_repository,
        user_repository,
        "claude-opus-5",
    )


@pytest.mark.asyncio
async def test_send_message_without_client_raises(
    blog_post_repository: InMemoryBlogPostRepository,
    user_repository: InMemoryUserRepository,
) -> None:
    unconfigured = ChatService(None, blog_post_repository, user_repository, "claude-opus-5")

    with pytest.raises(ChatNotConfiguredError):
        await unconfigured.send_message([ChatTurn(role="user", content="hi")], None, None)


@pytest.mark.asyncio
async def test_send_message_returns_reply_text(
    service: ChatService, fake_anthropic_client: FakeAnthropicClient
) -> None:
    reply = await service.send_message(
        [ChatTurn(role="user", content="What parts do you carry?")], None, None
    )

    assert reply == fake_anthropic_client.messages.reply


@pytest.mark.asyncio
async def test_visitor_system_prompt_mentions_registration(
    service: ChatService, fake_anthropic_client: FakeAnthropicClient
) -> None:
    await service.send_message([ChatTurn(role="user", content="Do I need an account?")], None, None)

    system_prompt = fake_anthropic_client.messages.last_kwargs["system"]
    assert "register" in system_prompt.lower()


@pytest.mark.asyncio
async def test_customer_system_prompt_includes_name(
    service: ChatService,
    fake_anthropic_client: FakeAnthropicClient,
) -> None:
    customer = AuthenticatedUser(
        id=CUSTOMER_ID, email_address="taylor@example.com", full_name="Taylor Customer", role=UserRole.CUSTOMER
    )

    await service.send_message([ChatTurn(role="user", content="Where's my order?")], customer, None)

    system_prompt = fake_anthropic_client.messages.last_kwargs["system"]
    assert "Taylor Customer" in system_prompt


@pytest.mark.asyncio
async def test_admin_system_prompt_includes_stats(
    service: ChatService,
    fake_anthropic_client: FakeAnthropicClient,
    blog_post_repository: InMemoryBlogPostRepository,
) -> None:
    await blog_post_repository.add(_published_post())
    admin = AuthenticatedUser(
        id=ADMIN_ID, email_address="admin@example.com", full_name="Alex Admin", role=UserRole.ADMIN
    )

    await service.send_message([ChatTurn(role="user", content="How many blog posts?")], admin, None)

    system_prompt = fake_anthropic_client.messages.last_kwargs["system"]
    assert "Alex Admin" in system_prompt
    assert "Choosing a Barrel Length" in system_prompt


@pytest.mark.asyncio
async def test_page_context_included_when_provided(
    service: ChatService, fake_anthropic_client: FakeAnthropicClient
) -> None:
    await service.send_message(
        [ChatTurn(role="user", content="What does this page offer?")], None, "Parts catalog page"
    )

    system_prompt = fake_anthropic_client.messages.last_kwargs["system"]
    assert "Parts catalog page" in system_prompt
