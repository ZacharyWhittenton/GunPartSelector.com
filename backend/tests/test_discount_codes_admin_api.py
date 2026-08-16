from uuid import UUID

from fastapi.testclient import TestClient

from site_api.domain.users import UserRole
from tests.conftest import InMemoryUserRepository

_CREATE_PAYLOAD = {
    "code": "SAVE10",
    "discountType": "percent",
    "value": 10,
    "expiresAt": None,
    "maxRedemptions": None,
}


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


def test_list_discount_codes_requires_admin(client: TestClient) -> None:
    user = _register(client, "client@example.com")

    response = client.get(
        "/api/admin/discount-codes",
        headers=_auth_headers(user["accessToken"]),
    )

    assert response.status_code == 403


async def test_create_and_list_discount_codes(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)

    create_response = client.post(
        "/api/admin/discount-codes",
        json=_CREATE_PAYLOAD,
        headers=_auth_headers(token),
    )
    assert create_response.status_code == 201
    assert create_response.json()["code"] == "SAVE10"
    assert create_response.json()["isActive"] is True

    list_response = client.get("/api/admin/discount-codes", headers=_auth_headers(token))
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


async def test_create_discount_code_rejects_duplicate(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)
    client.post("/api/admin/discount-codes", json=_CREATE_PAYLOAD, headers=_auth_headers(token))

    response = client.post(
        "/api/admin/discount-codes",
        json={**_CREATE_PAYLOAD, "code": "save10"},
        headers=_auth_headers(token),
    )

    assert response.status_code == 409


async def test_create_discount_code_rejects_percent_over_100(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)

    response = client.post(
        "/api/admin/discount-codes",
        json={**_CREATE_PAYLOAD, "value": 150},
        headers=_auth_headers(token),
    )

    assert response.status_code == 422


async def test_update_discount_code(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)
    created = client.post(
        "/api/admin/discount-codes", json=_CREATE_PAYLOAD, headers=_auth_headers(token)
    ).json()

    response = client.patch(
        f"/api/admin/discount-codes/{created['id']}",
        json={"discountType": "fixed", "value": 500, "expiresAt": None, "maxRedemptions": 5},
        headers=_auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["discountType"] == "fixed"
    assert response.json()["value"] == 500
    assert response.json()["maxRedemptions"] == 5


async def test_update_discount_code_404_when_missing(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)

    response = client.patch(
        f"/api/admin/discount-codes/{UUID(int=999)}",
        json={"discountType": "percent", "value": 10, "expiresAt": None, "maxRedemptions": None},
        headers=_auth_headers(token),
    )

    assert response.status_code == 404


async def test_deactivate_and_activate_discount_code(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)
    created = client.post(
        "/api/admin/discount-codes", json=_CREATE_PAYLOAD, headers=_auth_headers(token)
    ).json()

    deactivate_response = client.post(
        f"/api/admin/discount-codes/{created['id']}/deactivate",
        headers=_auth_headers(token),
    )
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["isActive"] is False

    activate_response = client.post(
        f"/api/admin/discount-codes/{created['id']}/activate",
        headers=_auth_headers(token),
    )
    assert activate_response.status_code == 200
    assert activate_response.json()["isActive"] is True


async def test_delete_discount_code(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)
    created = client.post(
        "/api/admin/discount-codes", json=_CREATE_PAYLOAD, headers=_auth_headers(token)
    ).json()

    response = client.delete(
        f"/api/admin/discount-codes/{created['id']}",
        headers=_auth_headers(token),
    )

    assert response.status_code == 204

    list_response = client.get("/api/admin/discount-codes", headers=_auth_headers(token))
    assert list_response.json() == []


async def test_delete_discount_code_404_when_missing(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)

    response = client.delete(
        f"/api/admin/discount-codes/{UUID(int=999)}",
        headers=_auth_headers(token),
    )

    assert response.status_code == 404
