from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from site_api.domain.users import UserRole
from tests.conftest import FakeFileStorage, InMemoryBlogPostRepository, InMemoryUserRepository


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


_POST_PAYLOAD = {
    "title": "Sealing Your Parking Lot",
    "excerpt": "Why sealing matters.",
    "body": "Full post body.",
    "tags": ["Asphalt", "Maintenance"],
    "coverImageUrl": None,
}


def test_create_post_requires_authentication(client: TestClient) -> None:
    response = client.post("/api/admin/blog/posts", json=_POST_PAYLOAD)

    assert response.status_code == 401


def test_create_post_forbidden_for_customer(client: TestClient) -> None:
    token = _register(client, "taylor@example.com")["accessToken"]

    response = client.post(
        "/api/admin/blog/posts",
        json=_POST_PAYLOAD,
        headers=_auth_headers(token),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_post_succeeds_as_admin(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    admin_token = await _make_admin_token(client, user_repository)

    response = client.post(
        "/api/admin/blog/posts",
        json=_POST_PAYLOAD,
        headers=_auth_headers(admin_token),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "draft"
    assert body["slug"] == "sealing-your-parking-lot"
    assert body["tags"] == ["asphalt", "maintenance"]


@pytest.mark.asyncio
async def test_list_all_posts_includes_drafts(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    admin_token = await _make_admin_token(client, user_repository)
    client.post("/api/admin/blog/posts", json=_POST_PAYLOAD, headers=_auth_headers(admin_token))

    response = client.get("/api/admin/blog/posts", headers=_auth_headers(admin_token))

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["status"] == "draft"


@pytest.mark.asyncio
async def test_update_post(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    admin_token = await _make_admin_token(client, user_repository)
    created = client.post(
        "/api/admin/blog/posts", json=_POST_PAYLOAD, headers=_auth_headers(admin_token)
    ).json()

    updated_payload = {**_POST_PAYLOAD, "title": "Updated Title"}
    response = client.patch(
        f"/api/admin/blog/posts/{created['id']}",
        json=updated_payload,
        headers=_auth_headers(admin_token),
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Updated Title"


@pytest.mark.asyncio
async def test_update_post_returns_404_when_missing(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    admin_token = await _make_admin_token(client, user_repository)

    response = client.patch(
        "/api/admin/blog/posts/11111111-1111-1111-1111-111111111111",
        json=_POST_PAYLOAD,
        headers=_auth_headers(admin_token),
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_publish_and_unpublish_post(
    client: TestClient,
    user_repository: InMemoryUserRepository,
    blog_post_repository: InMemoryBlogPostRepository,
) -> None:
    admin_token = await _make_admin_token(client, user_repository)
    created = client.post(
        "/api/admin/blog/posts", json=_POST_PAYLOAD, headers=_auth_headers(admin_token)
    ).json()

    publish_response = client.post(
        f"/api/admin/blog/posts/{created['id']}/publish",
        headers=_auth_headers(admin_token),
    )
    assert publish_response.status_code == 200
    assert publish_response.json()["status"] == "published"

    public_response = client.get("/api/blog/posts")
    assert len(public_response.json()) == 1

    unpublish_response = client.post(
        f"/api/admin/blog/posts/{created['id']}/unpublish",
        headers=_auth_headers(admin_token),
    )
    assert unpublish_response.status_code == 200
    assert unpublish_response.json()["status"] == "draft"

    public_after = client.get("/api/blog/posts")
    assert len(public_after.json()) == 0


@pytest.mark.asyncio
async def test_delete_post(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    admin_token = await _make_admin_token(client, user_repository)
    created = client.post(
        "/api/admin/blog/posts", json=_POST_PAYLOAD, headers=_auth_headers(admin_token)
    ).json()

    response = client.delete(
        f"/api/admin/blog/posts/{created['id']}",
        headers=_auth_headers(admin_token),
    )

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_upload_image_succeeds(
    client: TestClient,
    user_repository: InMemoryUserRepository,
    file_storage: FakeFileStorage,
) -> None:
    admin_token = await _make_admin_token(client, user_repository)

    response = client.post(
        "/api/admin/blog/images",
        files={"file": ("photo.jpg", b"fake-image-bytes", "image/jpeg")},
        headers=_auth_headers(admin_token),
    )

    assert response.status_code == 201
    assert response.json()["url"].startswith("/api/uploads/blog/")
    assert len(file_storage.saved) == 1


@pytest.mark.asyncio
async def test_upload_image_rejects_unsupported_type(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    admin_token = await _make_admin_token(client, user_repository)

    response = client.post(
        "/api/admin/blog/images",
        files={"file": ("doc.pdf", b"not-an-image", "application/pdf")},
        headers=_auth_headers(admin_token),
    )

    assert response.status_code == 415


@pytest.mark.asyncio
async def test_upload_image_rejects_oversized_file(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    admin_token = await _make_admin_token(client, user_repository)
    oversized_content = b"x" * (5 * 1024 * 1024 + 1)

    response = client.post(
        "/api/admin/blog/images",
        files={"file": ("huge.jpg", oversized_content, "image/jpeg")},
        headers=_auth_headers(admin_token),
    )

    assert response.status_code == 413


def test_upload_image_requires_admin(client: TestClient) -> None:
    response = client.post(
        "/api/admin/blog/images",
        files={"file": ("photo.jpg", b"fake-image-bytes", "image/jpeg")},
    )

    assert response.status_code == 401
