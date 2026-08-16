from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from site_api.db.models import BlogPostRecord, CommentRecord, TagSubscriptionRecord
from site_api.db.repositories import (
    SqlAlchemyBlogPostRepository,
    SqlAlchemyCommentRepository,
    SqlAlchemyTagSubscriptionRepository,
)
from site_api.domain.blog import BlogPost, Comment, PostNotFoundError, PostStatus

POST_ID = UUID("9a53d09a-f258-4b09-9fb3-ef6df4c2f9fd")
AUTHOR_ID = UUID("11111111-1111-1111-1111-111111111111")


class FakeSession:
    def __init__(
        self,
        records: dict[UUID, object] | None = None,
        query_result: object = None,
    ) -> None:
        self.added: list[object] = []
        self.deleted: list[object] = []
        self.flushed = False
        self._records = records or {}
        self._query_result = query_result

    def add(self, record: object) -> None:
        self.added.append(record)

    async def flush(self) -> None:
        self.flushed = True

    async def delete(self, record: object) -> None:
        self.deleted.append(record)

    async def get(self, _model_cls: object, pk: UUID) -> object | None:
        return self._records.get(pk)

    async def execute(self, _statement: object) -> _Result:
        return _Result(self._query_result)


class _Result:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object | None:
        return self._value

    def scalars(self) -> _Scalars:
        return _Scalars(self._value if isinstance(self._value, list) else [])


class _Scalars:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def all(self) -> list[object]:
        return self._values


def _make_post(**overrides: object) -> BlogPost:
    defaults: dict[str, object] = {
        "id": POST_ID,
        "title": "Sealing Your Parking Lot",
        "slug": "sealing-your-parking-lot",
        "excerpt": "Why sealing matters.",
        "body": "Full post body.",
        "cover_image_url": None,
        "tags": ("asphalt", "maintenance"),
        "author_id": AUTHOR_ID,
        "author_name": "Admin Person",
        "status": PostStatus.DRAFT,
        "published_at": None,
        "created_at": datetime(2026, 8, 9, 12, 0, tzinfo=UTC),
        "updated_at": datetime(2026, 8, 9, 12, 0, tzinfo=UTC),
    }
    defaults.update(overrides)
    return BlogPost(**defaults)


def _make_post_record(**overrides: object) -> BlogPostRecord:
    defaults: dict[str, object] = {
        "id": POST_ID,
        "title": "Sealing Your Parking Lot",
        "slug": "sealing-your-parking-lot",
        "excerpt": "Why sealing matters.",
        "body": "Full post body.",
        "cover_image_url": None,
        "tags": ["asphalt", "maintenance"],
        "author_id": AUTHOR_ID,
        "author_name": "Admin Person",
        "status": "draft",
        "published_at": None,
        "created_at": datetime(2026, 8, 9, 12, 0, tzinfo=UTC),
        "updated_at": datetime(2026, 8, 9, 12, 0, tzinfo=UTC),
    }
    defaults.update(overrides)
    return BlogPostRecord(**defaults)


@pytest.mark.asyncio
async def test_add_post_maps_and_flushes() -> None:
    session = FakeSession()
    repository = SqlAlchemyBlogPostRepository(cast(AsyncSession, session))
    post = _make_post()

    result = await repository.add(post)

    assert result is post
    assert session.flushed is True
    record = session.added[0]
    assert isinstance(record, BlogPostRecord)
    assert record.tags == ["asphalt", "maintenance"]


@pytest.mark.asyncio
async def test_update_post_mutates_record() -> None:
    record = _make_post_record()
    session = FakeSession(records={POST_ID: record})
    repository = SqlAlchemyBlogPostRepository(cast(AsyncSession, session))
    updated = _make_post(title="New Title", status=PostStatus.PUBLISHED)

    result = await repository.update(updated)

    assert result.title == "New Title"
    assert record.title == "New Title"
    assert record.status == "published"


@pytest.mark.asyncio
async def test_update_post_raises_when_missing() -> None:
    session = FakeSession()
    repository = SqlAlchemyBlogPostRepository(cast(AsyncSession, session))

    with pytest.raises(PostNotFoundError):
        await repository.update(_make_post())


@pytest.mark.asyncio
async def test_delete_post_removes_record() -> None:
    record = _make_post_record()
    session = FakeSession(records={POST_ID: record})
    repository = SqlAlchemyBlogPostRepository(cast(AsyncSession, session))

    await repository.delete(POST_ID)

    assert session.deleted == [record]


@pytest.mark.asyncio
async def test_delete_post_raises_when_missing() -> None:
    session = FakeSession()
    repository = SqlAlchemyBlogPostRepository(cast(AsyncSession, session))

    with pytest.raises(PostNotFoundError):
        await repository.delete(POST_ID)


@pytest.mark.asyncio
async def test_get_by_slug_maps_record() -> None:
    record = _make_post_record()
    session = FakeSession(query_result=record)
    repository = SqlAlchemyBlogPostRepository(cast(AsyncSession, session))

    post = await repository.get_by_slug("sealing-your-parking-lot")

    assert post is not None
    assert post.slug == record.slug


@pytest.mark.asyncio
async def test_slug_exists_true_and_false() -> None:
    session_with_match = FakeSession(query_result=POST_ID)
    repo_with_match = SqlAlchemyBlogPostRepository(cast(AsyncSession, session_with_match))
    assert await repo_with_match.slug_exists("sealing-your-parking-lot") is True

    session_without_match = FakeSession(query_result=None)
    repo_without_match = SqlAlchemyBlogPostRepository(cast(AsyncSession, session_without_match))
    assert await repo_without_match.slug_exists("nonexistent") is False


@pytest.mark.asyncio
async def test_list_all_maps_every_record() -> None:
    first = _make_post_record()
    second = _make_post_record(id=UUID(int=2), slug="other-post")
    session = FakeSession(query_result=[first, second])
    repository = SqlAlchemyBlogPostRepository(cast(AsyncSession, session))

    posts = await repository.list_all()

    assert [p.id for p in posts] == [first.id, second.id]


@pytest.mark.asyncio
async def test_list_distinct_published_tags_flattens_and_dedupes() -> None:
    session = FakeSession(query_result=[["asphalt", "striping"], ["striping", "concrete"]])
    repository = SqlAlchemyBlogPostRepository(cast(AsyncSession, session))

    tags = await repository.list_distinct_published_tags()

    assert tags == ["asphalt", "concrete", "striping"]


def _make_comment(**overrides: object) -> Comment:
    defaults: dict[str, object] = {
        "id": UUID(int=5),
        "post_id": POST_ID,
        "author_id": AUTHOR_ID,
        "author_name": "Taylor Client",
        "body": "Great post!",
        "created_at": datetime(2026, 8, 9, 12, 0, tzinfo=UTC),
    }
    defaults.update(overrides)
    return Comment(**defaults)


@pytest.mark.asyncio
async def test_add_comment_maps_and_flushes() -> None:
    session = FakeSession()
    repository = SqlAlchemyCommentRepository(cast(AsyncSession, session))
    comment = _make_comment()

    result = await repository.add(comment)

    assert result is comment
    record = session.added[0]
    assert isinstance(record, CommentRecord)
    assert record.body == comment.body


@pytest.mark.asyncio
async def test_list_for_post_maps_records() -> None:
    record = CommentRecord(
        id=UUID(int=5),
        post_id=POST_ID,
        author_id=AUTHOR_ID,
        author_name="Taylor Client",
        body="Great post!",
        created_at=datetime(2026, 8, 9, 12, 0, tzinfo=UTC),
    )
    session = FakeSession(query_result=[record])
    repository = SqlAlchemyCommentRepository(cast(AsyncSession, session))

    comments = await repository.list_for_post(POST_ID)

    assert len(comments) == 1
    assert comments[0].body == "Great post!"


@pytest.mark.asyncio
async def test_delete_comment_removes_record() -> None:
    record = CommentRecord(
        id=UUID(int=5),
        post_id=POST_ID,
        author_id=AUTHOR_ID,
        author_name="Taylor Client",
        body="Great post!",
        created_at=datetime(2026, 8, 9, 12, 0, tzinfo=UTC),
    )
    session = FakeSession(records={UUID(int=5): record})
    repository = SqlAlchemyCommentRepository(cast(AsyncSession, session))

    await repository.delete(UUID(int=5))

    assert session.deleted == [record]


@pytest.mark.asyncio
async def test_subscription_add_maps_and_flushes() -> None:
    session = FakeSession()
    repository = SqlAlchemyTagSubscriptionRepository(cast(AsyncSession, session))
    from site_api.domain.blog import TagSubscription

    subscription = TagSubscription(
        id=UUID(int=7),
        user_id=AUTHOR_ID,
        tag_name="asphalt",
        created_at=datetime(2026, 8, 9, 12, 0, tzinfo=UTC),
    )

    result = await repository.add(subscription)

    assert result is subscription
    record = session.added[0]
    assert isinstance(record, TagSubscriptionRecord)
    assert record.tag_name == "asphalt"


@pytest.mark.asyncio
async def test_subscription_get_returns_none_when_missing() -> None:
    session = FakeSession(query_result=None)
    repository = SqlAlchemyTagSubscriptionRepository(cast(AsyncSession, session))

    result = await repository.get(AUTHOR_ID, "asphalt")

    assert result is None


@pytest.mark.asyncio
async def test_subscription_remove_deletes_when_found() -> None:
    record = TagSubscriptionRecord(
        id=UUID(int=7),
        user_id=AUTHOR_ID,
        tag_name="asphalt",
        created_at=datetime(2026, 8, 9, 12, 0, tzinfo=UTC),
    )
    session = FakeSession(query_result=record)
    repository = SqlAlchemyTagSubscriptionRepository(cast(AsyncSession, session))

    await repository.remove(AUTHOR_ID, "asphalt")

    assert session.deleted == [record]


@pytest.mark.asyncio
async def test_subscription_remove_noop_when_missing() -> None:
    session = FakeSession(query_result=None)
    repository = SqlAlchemyTagSubscriptionRepository(cast(AsyncSession, session))

    await repository.remove(AUTHOR_ID, "asphalt")

    assert session.deleted == []
