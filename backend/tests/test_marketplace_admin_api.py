from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient

from site_api.domain.marketplace import MarketplaceItem
from site_api.domain.users import UserRole
from tests.conftest import InMemoryMarketplaceItemRepository, InMemoryUserRepository


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


def _make_item(**overrides: object) -> MarketplaceItem:
    now = datetime.now(UTC)
    defaults: dict[str, object] = {
        "id": UUID(int=1),
        "name": "Website Audit",
        "slug": "website-audit",
        "description": "A full technical and SEO audit.",
        "price_cents": 5000,
        "image_url": None,
        "is_active": True,
        "created_by_admin_id": UUID(int=100),
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return MarketplaceItem(**defaults)


_ITEM_PAYLOAD = {
    "name": "Website Audit",
    "description": "A full technical and SEO audit.",
    "priceCents": 5000,
    "imageUrl": None,
}


def test_list_all_items_requires_admin(client: TestClient) -> None:
    user = _register(client, "client@example.com")

    response = client.get(
        "/api/admin/marketplace/items",
        headers=_auth_headers(user["accessToken"]),
    )

    assert response.status_code == 403


async def test_create_and_list_items_as_admin(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)

    create_response = client.post(
        "/api/admin/marketplace/items",
        json=_ITEM_PAYLOAD,
        headers=_auth_headers(token),
    )
    assert create_response.status_code == 201
    assert create_response.json()["slug"] == "website-audit"

    list_response = client.get(
        "/api/admin/marketplace/items",
        headers=_auth_headers(token),
    )
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


async def test_update_item_404_when_missing(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)

    response = client.patch(
        f"/api/admin/marketplace/items/{UUID(int=999)}",
        json=_ITEM_PAYLOAD,
        headers=_auth_headers(token),
    )

    assert response.status_code == 404


async def test_update_item_success(
    client: TestClient,
    user_repository: InMemoryUserRepository,
    marketplace_item_repository: InMemoryMarketplaceItemRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)
    marketplace_item_repository.items.append(_make_item())

    response = client.patch(
        f"/api/admin/marketplace/items/{UUID(int=1)}",
        json={**_ITEM_PAYLOAD, "priceCents": 7500},
        headers=_auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["priceCents"] == 7500


async def test_deactivate_and_activate_item(
    client: TestClient,
    user_repository: InMemoryUserRepository,
    marketplace_item_repository: InMemoryMarketplaceItemRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)
    marketplace_item_repository.items.append(_make_item())

    deactivate_response = client.post(
        f"/api/admin/marketplace/items/{UUID(int=1)}/deactivate",
        headers=_auth_headers(token),
    )
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["isActive"] is False

    activate_response = client.post(
        f"/api/admin/marketplace/items/{UUID(int=1)}/activate",
        headers=_auth_headers(token),
    )
    assert activate_response.status_code == 200
    assert activate_response.json()["isActive"] is True


async def test_deactivate_item_404_when_missing(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)

    response = client.post(
        f"/api/admin/marketplace/items/{UUID(int=999)}/deactivate",
        headers=_auth_headers(token),
    )

    assert response.status_code == 404


async def test_delete_item_success(
    client: TestClient,
    user_repository: InMemoryUserRepository,
    marketplace_item_repository: InMemoryMarketplaceItemRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)
    marketplace_item_repository.items.append(_make_item())

    response = client.delete(
        f"/api/admin/marketplace/items/{UUID(int=1)}",
        headers=_auth_headers(token),
    )

    assert response.status_code == 204


async def test_delete_item_404_when_missing(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)

    response = client.delete(
        f"/api/admin/marketplace/items/{UUID(int=999)}",
        headers=_auth_headers(token),
    )

    assert response.status_code == 404


async def test_delete_item_conflict_when_it_has_orders(
    client: TestClient,
    user_repository: InMemoryUserRepository,
    marketplace_item_repository: InMemoryMarketplaceItemRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)
    marketplace_item_repository.items.append(_make_item())
    client.post(
        "/api/marketplace/checkout",
        json={"items": [{"itemId": str(UUID(int=1)), "quantity": 1}]},
    )

    response = client.delete(
        f"/api/admin/marketplace/items/{UUID(int=1)}",
        headers=_auth_headers(token),
    )

    assert response.status_code == 409


async def test_upload_item_image_success(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)

    response = client.post(
        "/api/admin/marketplace/items/images",
        files={"file": ("photo.jpg", b"fake-image-bytes", "image/jpeg")},
        headers=_auth_headers(token),
    )

    assert response.status_code == 201
    assert "url" in response.json()


async def test_upload_item_image_rejects_unsupported_type(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)

    response = client.post(
        "/api/admin/marketplace/items/images",
        files={"file": ("doc.pdf", b"not-an-image", "application/pdf")},
        headers=_auth_headers(token),
    )

    assert response.status_code == 415


async def test_upload_item_image_rejects_oversized_file(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)
    oversized_content = b"x" * (5 * 1024 * 1024 + 1)

    response = client.post(
        "/api/admin/marketplace/items/images",
        files={"file": ("huge.jpg", oversized_content, "image/jpeg")},
        headers=_auth_headers(token),
    )

    assert response.status_code == 413


async def test_list_all_orders_filters_by_status(
    client: TestClient,
    user_repository: InMemoryUserRepository,
    marketplace_item_repository: InMemoryMarketplaceItemRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)
    marketplace_item_repository.items.append(_make_item())
    client.post(
        "/api/marketplace/checkout",
        json={"items": [{"itemId": str(UUID(int=1)), "quantity": 1}]},
    )

    open_response = client.get(
        "/api/admin/marketplace/orders?status=open",
        headers=_auth_headers(token),
    )
    assert open_response.status_code == 200
    assert len(open_response.json()) == 1

    paid_response = client.get(
        "/api/admin/marketplace/orders?status=paid",
        headers=_auth_headers(token),
    )
    assert paid_response.status_code == 200
    assert paid_response.json() == []
