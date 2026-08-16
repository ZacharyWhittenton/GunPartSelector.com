from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from loguru import logger

from site_api.core.slugify import slugify
from site_api.domain.blog import (
    BlogPost,
    BlogPostRepository,
    Comment,
    CommentNotFoundError,
    CommentRepository,
    NotCommentAuthorError,
    PostNotFoundError,
    PostStatus,
    TagSubscription,
    TagSubscriptionRepository,
)
from site_api.domain.users import UserRole


@dataclass(frozen=True, slots=True)
class CreatePost:
    title: str
    excerpt: str
    body: str
    tags: tuple[str, ...]
    cover_image_url: str | None
    author_id: UUID
    author_name: str


@dataclass(frozen=True, slots=True)
class UpdatePost:
    title: str
    excerpt: str
    body: str
    tags: tuple[str, ...]
    cover_image_url: str | None


@dataclass(frozen=True, slots=True)
class AddComment:
    post_id: UUID
    author_id: UUID
    author_name: str
    body: str


def _normalize_tags(tags: tuple[str, ...]) -> tuple[str, ...]:
    seen: dict[str, None] = {}
    for tag in tags:
        cleaned = tag.strip().lower()
        if cleaned:
            seen[cleaned] = None
    return tuple(seen.keys())


class BlogService:
    def __init__(
        self,
        post_repository: BlogPostRepository,
        comment_repository: CommentRepository,
        subscription_repository: TagSubscriptionRepository,
        id_factory: Callable[[], UUID] = uuid4,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._posts = post_repository
        self._comments = comment_repository
        self._subscriptions = subscription_repository
        self._id_factory = id_factory
        self._clock = clock

    async def create_post(self, command: CreatePost) -> BlogPost:
        slug = await self._unique_slug(command.title)
        now = self._clock()
        post = BlogPost(
            id=self._id_factory(),
            title=command.title,
            slug=slug,
            excerpt=command.excerpt,
            body=command.body,
            cover_image_url=command.cover_image_url,
            tags=_normalize_tags(command.tags),
            author_id=command.author_id,
            author_name=command.author_name,
            status=PostStatus.DRAFT,
            published_at=None,
            created_at=now,
            updated_at=now,
        )
        saved = await self._posts.add(post)
        logger.bind(post_id=str(saved.id)).info("Blog post created")
        return saved

    async def update_post(self, post_id: UUID, command: UpdatePost) -> BlogPost:
        post = await self._posts.get_by_id(post_id)
        if post is None:
            raise PostNotFoundError

        updated = replace(
            post,
            title=command.title,
            excerpt=command.excerpt,
            body=command.body,
            tags=_normalize_tags(command.tags),
            cover_image_url=command.cover_image_url,
            updated_at=self._clock(),
        )
        return await self._posts.update(updated)

    async def publish_post(self, post_id: UUID) -> BlogPost:
        post = await self._posts.get_by_id(post_id)
        if post is None:
            raise PostNotFoundError

        now = self._clock()
        updated = replace(
            post,
            status=PostStatus.PUBLISHED,
            published_at=post.published_at or now,
            updated_at=now,
        )
        return await self._posts.update(updated)

    async def unpublish_post(self, post_id: UUID) -> BlogPost:
        post = await self._posts.get_by_id(post_id)
        if post is None:
            raise PostNotFoundError

        updated = replace(post, status=PostStatus.DRAFT, updated_at=self._clock())
        return await self._posts.update(updated)

    async def delete_post(self, post_id: UUID) -> None:
        await self._posts.delete(post_id)

    async def list_posts_for_admin(self) -> list[BlogPost]:
        return await self._posts.list_all()

    async def list_published_posts(self, tag: str | None = None) -> list[BlogPost]:
        normalized_tag = tag.strip().lower() if tag else None
        return await self._posts.list_published(normalized_tag)

    async def get_post_for_viewer(self, slug: str, viewer_role: UserRole | None) -> BlogPost:
        post = await self._posts.get_by_slug(slug)
        if post is None:
            raise PostNotFoundError

        if post.status is PostStatus.DRAFT and viewer_role is not UserRole.ADMIN:
            raise PostNotFoundError

        return post

    async def list_tags(self) -> list[str]:
        return await self._posts.list_distinct_published_tags()

    async def add_comment(self, command: AddComment) -> Comment:
        post = await self._posts.get_by_id(command.post_id)
        if post is None or post.status is not PostStatus.PUBLISHED:
            raise PostNotFoundError

        comment = Comment(
            id=self._id_factory(),
            post_id=command.post_id,
            author_id=command.author_id,
            author_name=command.author_name,
            body=command.body,
            created_at=self._clock(),
        )
        return await self._comments.add(comment)

    async def list_comments(self, post_id: UUID, viewer_role: UserRole | None) -> list[Comment]:
        post = await self._posts.get_by_id(post_id)
        if post is None:
            raise PostNotFoundError
        if post.status is PostStatus.DRAFT and viewer_role is not UserRole.ADMIN:
            raise PostNotFoundError

        return await self._comments.list_for_post(post_id)

    async def delete_comment(
        self, comment_id: UUID, requesting_user_id: UUID, is_admin: bool
    ) -> None:
        comment = await self._comments.get_by_id(comment_id)
        if comment is None:
            raise CommentNotFoundError

        if not is_admin and comment.author_id != requesting_user_id:
            raise NotCommentAuthorError

        await self._comments.delete(comment_id)

    async def subscribe_to_tag(self, user_id: UUID, tag_name: str) -> TagSubscription:
        normalized = tag_name.strip().lower()
        existing = await self._subscriptions.get(user_id, normalized)
        if existing is not None:
            return existing

        subscription = TagSubscription(
            id=self._id_factory(),
            user_id=user_id,
            tag_name=normalized,
            created_at=self._clock(),
        )
        return await self._subscriptions.add(subscription)

    async def unsubscribe_from_tag(self, user_id: UUID, tag_name: str) -> None:
        await self._subscriptions.remove(user_id, tag_name.strip().lower())

    async def list_subscriptions(self, user_id: UUID) -> list[TagSubscription]:
        return await self._subscriptions.list_for_user(user_id)

    async def _unique_slug(self, title: str) -> str:
        base_slug = slugify(title)
        slug = base_slug
        suffix = 2
        while await self._posts.slug_exists(slug):
            slug = f"{base_slug}-{suffix}"
            suffix += 1
        return slug
