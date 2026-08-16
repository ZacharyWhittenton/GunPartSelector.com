from datetime import UTC, datetime
from itertools import count
from uuid import UUID

import pytest

from site_api.domain.blog import PostNotFoundError, PostStatus
from site_api.domain.users import UserRole
from site_api.services.blog import AddComment, BlogService, CreatePost, UpdatePost
from tests.conftest import (
    InMemoryBlogPostRepository,
    InMemoryCommentRepository,
    InMemoryTagSubscriptionRepository,
)

ADMIN_ID = UUID("11111111-1111-1111-1111-111111111111")
CUSTOMER_ID = UUID("22222222-2222-2222-2222-222222222222")
OTHER_CUSTOMER_ID = UUID("33333333-3333-3333-3333-333333333333")


@pytest.fixture
def service(
    blog_post_repository: InMemoryBlogPostRepository,
    comment_repository: InMemoryCommentRepository,
    tag_subscription_repository: InMemoryTagSubscriptionRepository,
) -> BlogService:
    ids = iter(UUID(int=n) for n in count(1))
    return BlogService(
        blog_post_repository,
        comment_repository,
        tag_subscription_repository,
        id_factory=lambda: next(ids),
        clock=lambda: datetime(2026, 8, 9, 12, 0, tzinfo=UTC),
    )


def _create_command(**overrides: object) -> CreatePost:
    defaults: dict[str, object] = {
        "title": "Sealing Your Parking Lot",
        "excerpt": "Why sealing matters.",
        "body": "Full post body.",
        "tags": ("Asphalt", "asphalt", "  Maintenance  "),
        "cover_image_url": None,
        "author_id": ADMIN_ID,
        "author_name": "Admin Person",
    }
    defaults.update(overrides)
    return CreatePost(**defaults)


@pytest.mark.asyncio
async def test_create_post_generates_slug_and_normalizes_tags(service: BlogService) -> None:
    post = await service.create_post(_create_command())

    assert post.slug == "sealing-your-parking-lot"
    assert post.status is PostStatus.DRAFT
    assert post.tags == ("asphalt", "maintenance")


@pytest.mark.asyncio
async def test_create_post_deduplicates_slug_collisions(service: BlogService) -> None:
    first = await service.create_post(_create_command())
    second = await service.create_post(_create_command())

    assert first.slug == "sealing-your-parking-lot"
    assert second.slug == "sealing-your-parking-lot-2"


@pytest.mark.asyncio
async def test_update_post_raises_when_missing(service: BlogService) -> None:
    with pytest.raises(PostNotFoundError):
        await service.update_post(
            UUID(int=999),
            UpdatePost(title="x", excerpt="x", body="x", tags=(), cover_image_url=None),
        )


@pytest.mark.asyncio
async def test_publish_then_unpublish_post(service: BlogService) -> None:
    post = await service.create_post(_create_command())

    published = await service.publish_post(post.id)
    assert published.status is PostStatus.PUBLISHED
    assert published.published_at is not None

    unpublished = await service.unpublish_post(post.id)
    assert unpublished.status is PostStatus.DRAFT
    assert unpublished.published_at == published.published_at


@pytest.mark.asyncio
async def test_delete_post(service: BlogService) -> None:
    post = await service.create_post(_create_command())

    await service.delete_post(post.id)

    with pytest.raises(PostNotFoundError):
        await service.get_post_for_viewer(post.slug, UserRole.ADMIN)


@pytest.mark.asyncio
async def test_get_post_for_viewer_hides_drafts_from_non_admins(service: BlogService) -> None:
    post = await service.create_post(_create_command())

    with pytest.raises(PostNotFoundError):
        await service.get_post_for_viewer(post.slug, None)

    with pytest.raises(PostNotFoundError):
        await service.get_post_for_viewer(post.slug, UserRole.CUSTOMER)

    visible = await service.get_post_for_viewer(post.slug, UserRole.ADMIN)
    assert visible.id == post.id


@pytest.mark.asyncio
async def test_list_published_posts_filters_by_tag(service: BlogService) -> None:
    post = await service.create_post(_create_command(tags=("striping",)))
    await service.publish_post(post.id)
    other = await service.create_post(_create_command(title="Different Post", tags=("concrete",)))
    await service.publish_post(other.id)

    striping_only = await service.list_published_posts(tag="striping")

    assert [p.id for p in striping_only] == [post.id]


@pytest.mark.asyncio
async def test_add_comment_requires_published_post(service: BlogService) -> None:
    post = await service.create_post(_create_command())

    with pytest.raises(PostNotFoundError):
        await service.add_comment(
            AddComment(
                post_id=post.id,
                author_id=CUSTOMER_ID,
                author_name="Taylor Client",
                body="Great post!",
            )
        )


@pytest.mark.asyncio
async def test_add_and_list_comments_on_published_post(service: BlogService) -> None:
    post = await service.create_post(_create_command())
    await service.publish_post(post.id)

    comment = await service.add_comment(
        AddComment(
            post_id=post.id,
            author_id=CUSTOMER_ID,
            author_name="Taylor Client",
            body="Great post!",
        )
    )

    comments = await service.list_comments(post.id, None)
    assert comments == [comment]


@pytest.mark.asyncio
async def test_delete_comment_by_author_succeeds(service: BlogService) -> None:
    post = await service.create_post(_create_command())
    await service.publish_post(post.id)
    comment = await service.add_comment(
        AddComment(
            post_id=post.id,
            author_id=CUSTOMER_ID,
            author_name="Taylor Client",
            body="Great post!",
        )
    )

    await service.delete_comment(comment.id, CUSTOMER_ID, is_admin=False)

    assert await service.list_comments(post.id, None) == []


@pytest.mark.asyncio
async def test_delete_comment_by_non_author_non_admin_fails(service: BlogService) -> None:
    from site_api.domain.blog import NotCommentAuthorError

    post = await service.create_post(_create_command())
    await service.publish_post(post.id)
    comment = await service.add_comment(
        AddComment(
            post_id=post.id,
            author_id=CUSTOMER_ID,
            author_name="Taylor Client",
            body="Great post!",
        )
    )

    with pytest.raises(NotCommentAuthorError):
        await service.delete_comment(comment.id, OTHER_CUSTOMER_ID, is_admin=False)


@pytest.mark.asyncio
async def test_delete_comment_by_admin_succeeds_even_if_not_author(service: BlogService) -> None:
    post = await service.create_post(_create_command())
    await service.publish_post(post.id)
    comment = await service.add_comment(
        AddComment(
            post_id=post.id,
            author_id=CUSTOMER_ID,
            author_name="Taylor Client",
            body="Great post!",
        )
    )

    await service.delete_comment(comment.id, ADMIN_ID, is_admin=True)

    assert await service.list_comments(post.id, None) == []


@pytest.mark.asyncio
async def test_subscribe_to_tag_is_idempotent(service: BlogService) -> None:
    first = await service.subscribe_to_tag(CUSTOMER_ID, "Asphalt")
    second = await service.subscribe_to_tag(CUSTOMER_ID, "asphalt")

    assert first.id == second.id
    subscriptions = await service.list_subscriptions(CUSTOMER_ID)
    assert [s.tag_name for s in subscriptions] == ["asphalt"]


@pytest.mark.asyncio
async def test_unsubscribe_from_tag(service: BlogService) -> None:
    await service.subscribe_to_tag(CUSTOMER_ID, "asphalt")

    await service.unsubscribe_from_tag(CUSTOMER_ID, "asphalt")

    assert await service.list_subscriptions(CUSTOMER_ID) == []
