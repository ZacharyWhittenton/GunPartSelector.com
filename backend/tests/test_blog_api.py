from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from site_api.domain.blog import BlogPost, PostStatus
from site_api.domain.users import UserRole
from tests.conftest import InMemoryBlogPostRepository, InMemoryUserRepository

AUTHOR_ID = UUID("11111111-1111-1111-1111-111111111111")


def _make_post(**overrides: object) -> BlogPost:
    defaults: dict[str, object] = {
        "id": UUID("9a53d09a-f258-4b09-9fb3-ef6df4c2f9fd"),
        "title": "Sealing Your Parking Lot",
        "slug": "sealing-your-parking-lot",
        "excerpt": "Why sealing matters.",
        "body": "Full post body.",
        "cover_image_url": None,
        "tags": ("asphalt", "maintenance"),
        "author_id": AUTHOR_ID,
        "author_name": "Admin Person",
        "status": PostStatus.PUBLISHED,
        "published_at": datetime(2026, 8, 9, 12, 0, tzinfo=UTC),
        "created_at": datetime(2026, 8, 9, 12, 0, tzinfo=UTC),
        "updated_at": datetime(2026, 8, 9, 12, 0, tzinfo=UTC),
    }
    defaults.update(overrides)
    return BlogPost(**defaults)


def _register(client: TestClient, email: str, full_name: str = "Test User") -> dict:
    response = client.post(
        "/api/auth/register",
        json={"emailAddress": email, "fullName": full_name, "password": "super-secret-1"},
    )
    assert response.status_code == 201
    return response.json()


def _login(client: TestClient, email: str) -> dict:
    response = client.post(
        "/api/auth/login",
        json={"emailAddress": email, "password": "super-secret-1"},
    )
    assert response.status_code == 200
    return response.json()


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _make_admin_token(client: TestClient, user_repository: InMemoryUserRepository) -> str:
    admin = _register(client, "admin@example.com", "Admin Person")
    await user_repository.update_role(UUID(admin["user"]["id"]), UserRole.ADMIN)
    return _login(client, "admin@example.com")["accessToken"]


def test_list_posts_returns_only_published(
    client: TestClient,
    blog_post_repository: InMemoryBlogPostRepository,
) -> None:
    published = _make_post()
    draft = _make_post(
        id=UUID(int=2),
        slug="draft-post",
        status=PostStatus.DRAFT,
        published_at=None,
    )
    blog_post_repository.posts.extend([published, draft])

    response = client.get("/api/blog/posts")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["slug"] == "sealing-your-parking-lot"


def test_get_published_post_by_slug(
    client: TestClient,
    blog_post_repository: InMemoryBlogPostRepository,
) -> None:
    blog_post_repository.posts.append(_make_post())

    response = client.get("/api/blog/posts/sealing-your-parking-lot")

    assert response.status_code == 200
    assert response.json()["body"] == "Full post body."


def test_get_draft_post_returns_404_for_anonymous(
    client: TestClient,
    blog_post_repository: InMemoryBlogPostRepository,
) -> None:
    blog_post_repository.posts.append(_make_post(status=PostStatus.DRAFT, published_at=None))

    response = client.get("/api/blog/posts/sealing-your-parking-lot")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_draft_post_visible_to_admin(
    client: TestClient,
    blog_post_repository: InMemoryBlogPostRepository,
    user_repository: InMemoryUserRepository,
) -> None:
    blog_post_repository.posts.append(_make_post(status=PostStatus.DRAFT, published_at=None))
    admin_token = await _make_admin_token(client, user_repository)

    response = client.get(
        "/api/blog/posts/sealing-your-parking-lot",
        headers=_auth_headers(admin_token),
    )

    assert response.status_code == 200


def test_get_draft_post_hidden_from_customer(
    client: TestClient,
    blog_post_repository: InMemoryBlogPostRepository,
) -> None:
    blog_post_repository.posts.append(_make_post(status=PostStatus.DRAFT, published_at=None))
    customer_token = _register(client, "taylor@example.com")["accessToken"]

    response = client.get(
        "/api/blog/posts/sealing-your-parking-lot",
        headers=_auth_headers(customer_token),
    )

    assert response.status_code == 404


def test_add_comment_requires_authentication(
    client: TestClient,
    blog_post_repository: InMemoryBlogPostRepository,
) -> None:
    blog_post_repository.posts.append(_make_post())

    response = client.post(
        "/api/blog/posts/sealing-your-parking-lot/comments",
        json={"body": "Great post!"},
    )

    assert response.status_code == 401


def test_add_and_list_comments(
    client: TestClient,
    blog_post_repository: InMemoryBlogPostRepository,
) -> None:
    blog_post_repository.posts.append(_make_post())
    customer_token = _register(client, "taylor@example.com")["accessToken"]

    add_response = client.post(
        "/api/blog/posts/sealing-your-parking-lot/comments",
        json={"body": "Great post!"},
        headers=_auth_headers(customer_token),
    )
    assert add_response.status_code == 201

    list_response = client.get("/api/blog/posts/sealing-your-parking-lot/comments")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["body"] == "Great post!"


def test_delete_comment_by_non_author_returns_403(
    client: TestClient,
    blog_post_repository: InMemoryBlogPostRepository,
) -> None:
    blog_post_repository.posts.append(_make_post())
    author_token = _register(client, "taylor@example.com")["accessToken"]
    other_token = _register(client, "jordan@example.com", "Jordan Customer")["accessToken"]

    comment = client.post(
        "/api/blog/posts/sealing-your-parking-lot/comments",
        json={"body": "Great post!"},
        headers=_auth_headers(author_token),
    ).json()

    response = client.delete(
        f"/api/blog/comments/{comment['id']}",
        headers=_auth_headers(other_token),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_comment_by_admin_succeeds(
    client: TestClient,
    blog_post_repository: InMemoryBlogPostRepository,
    user_repository: InMemoryUserRepository,
) -> None:
    blog_post_repository.posts.append(_make_post())
    author_token = _register(client, "taylor@example.com")["accessToken"]
    admin_token = await _make_admin_token(client, user_repository)

    comment = client.post(
        "/api/blog/posts/sealing-your-parking-lot/comments",
        json={"body": "Great post!"},
        headers=_auth_headers(author_token),
    ).json()

    response = client.delete(
        f"/api/blog/comments/{comment['id']}",
        headers=_auth_headers(admin_token),
    )

    assert response.status_code == 204


def test_list_tags(
    client: TestClient,
    blog_post_repository: InMemoryBlogPostRepository,
) -> None:
    blog_post_repository.posts.append(_make_post())

    response = client.get("/api/blog/tags")

    assert response.status_code == 200
    assert response.json() == ["asphalt", "maintenance"]


def test_subscriptions_require_authentication(client: TestClient) -> None:
    response = client.get("/api/blog/subscriptions")

    assert response.status_code == 401


def test_subscribe_list_and_unsubscribe(client: TestClient) -> None:
    token = _register(client, "taylor@example.com")["accessToken"]

    subscribe_response = client.post(
        "/api/blog/tags/asphalt/subscribe",
        headers=_auth_headers(token),
    )
    assert subscribe_response.status_code == 204

    list_response = client.get("/api/blog/subscriptions", headers=_auth_headers(token))
    assert list_response.json() == ["asphalt"]

    unsubscribe_response = client.delete(
        "/api/blog/tags/asphalt/subscribe",
        headers=_auth_headers(token),
    )
    assert unsubscribe_response.status_code == 204

    list_after = client.get("/api/blog/subscriptions", headers=_auth_headers(token))
    assert list_after.json() == []
