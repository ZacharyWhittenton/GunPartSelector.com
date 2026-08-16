from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID


class PostStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"


@dataclass(frozen=True, slots=True)
class BlogPost:
    id: UUID
    title: str
    slug: str
    excerpt: str
    body: str
    cover_image_url: str | None
    tags: tuple[str, ...]
    author_id: UUID
    author_name: str
    status: PostStatus
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class Comment:
    id: UUID
    post_id: UUID
    author_id: UUID
    author_name: str
    body: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class TagSubscription:
    id: UUID
    user_id: UUID
    tag_name: str
    created_at: datetime


class PostNotFoundError(Exception):
    """Raised when a referenced blog post does not exist or is not visible to the viewer."""


class CommentNotFoundError(Exception):
    """Raised when a referenced comment does not exist."""


class NotCommentAuthorError(Exception):
    """Raised when a non-admin tries to delete a comment they did not author."""


class BlogPostRepository(Protocol):
    async def add(self, post: BlogPost) -> BlogPost: ...

    async def update(self, post: BlogPost) -> BlogPost: ...

    async def delete(self, post_id: UUID) -> None: ...

    async def get_by_id(self, post_id: UUID) -> BlogPost | None: ...

    async def get_by_slug(self, slug: str) -> BlogPost | None: ...

    async def slug_exists(self, slug: str) -> bool: ...

    async def list_published(self, tag: str | None = None) -> list[BlogPost]: ...

    async def list_all(self) -> list[BlogPost]: ...

    async def list_distinct_published_tags(self) -> list[str]: ...


class CommentRepository(Protocol):
    async def add(self, comment: Comment) -> Comment: ...

    async def get_by_id(self, comment_id: UUID) -> Comment | None: ...

    async def list_for_post(self, post_id: UUID) -> list[Comment]: ...

    async def delete(self, comment_id: UUID) -> None: ...


class TagSubscriptionRepository(Protocol):
    async def add(self, subscription: TagSubscription) -> TagSubscription: ...

    async def remove(self, user_id: UUID, tag_name: str) -> None: ...

    async def get(self, user_id: UUID, tag_name: str) -> TagSubscription | None: ...

    async def list_for_user(self, user_id: UUID) -> list[TagSubscription]: ...
