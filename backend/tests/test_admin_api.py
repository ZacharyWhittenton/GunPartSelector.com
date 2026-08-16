from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from site_api.domain.users import UserRole
from tests.conftest import InMemoryUserRepository


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


@pytest.mark.asyncio
async def test_admin_endpoints_require_admin_role(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    admin = _register(client, "admin@example.com")
    await user_repository.update_role(UUID(admin["user"]["id"]), UserRole.ADMIN)
    admin_token = _login(client, "admin@example.com")["accessToken"]

    customer = _register(client, "customer@example.com")
    customer_token = customer["accessToken"]

    unauthenticated = client.get("/api/admin/users")
    as_customer = client.get("/api/admin/users", headers=_auth_headers(customer_token))
    as_admin = client.get("/api/admin/users", headers=_auth_headers(admin_token))

    assert unauthenticated.status_code == 401
    assert as_customer.status_code == 403
    assert as_admin.status_code == 200
    assert len(as_admin.json()) == 2


@pytest.mark.asyncio
async def test_admin_can_promote_and_demote_other_users(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    admin = _register(client, "admin@example.com")
    await user_repository.update_role(UUID(admin["user"]["id"]), UserRole.ADMIN)
    admin_token = _login(client, "admin@example.com")["accessToken"]

    customer = _register(client, "customer@example.com")
    customer_id = customer["user"]["id"]

    promote = client.patch(
        f"/api/admin/users/{customer_id}/role",
        json={"role": "admin"},
        headers=_auth_headers(admin_token),
    )
    demote = client.patch(
        f"/api/admin/users/{customer_id}/role",
        json={"role": "customer"},
        headers=_auth_headers(admin_token),
    )

    assert promote.status_code == 200
    assert promote.json()["role"] == "admin"
    assert demote.status_code == 200
    assert demote.json()["role"] == "customer"


@pytest.mark.asyncio
async def test_admin_cannot_change_own_role(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    admin = _register(client, "admin@example.com")
    admin_id = admin["user"]["id"]
    await user_repository.update_role(UUID(admin_id), UserRole.ADMIN)
    admin_token = _login(client, "admin@example.com")["accessToken"]

    response = client.patch(
        f"/api/admin/users/{admin_id}/role",
        json={"role": "customer"},
        headers=_auth_headers(admin_token),
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_role_update_for_unknown_user_returns_404(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    admin = _register(client, "admin@example.com")
    await user_repository.update_role(UUID(admin["user"]["id"]), UserRole.ADMIN)
    admin_token = _login(client, "admin@example.com")["accessToken"]

    response = client.patch(
        "/api/admin/users/11111111-1111-1111-1111-111111111111/role",
        json={"role": "admin"},
        headers=_auth_headers(admin_token),
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_can_suspend_and_reactivate_account(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    admin = _register(client, "admin@example.com")
    await user_repository.update_role(UUID(admin["user"]["id"]), UserRole.ADMIN)
    admin_token = _login(client, "admin@example.com")["accessToken"]

    customer = _register(client, "customer@example.com")
    customer_id = customer["user"]["id"]

    suspend = client.patch(
        f"/api/admin/users/{customer_id}/status",
        json={"status": "suspended"},
        headers=_auth_headers(admin_token),
    )
    assert suspend.status_code == 200
    assert suspend.json()["status"] == "suspended"

    blocked_login = client.post(
        "/api/auth/login",
        json={"emailAddress": "customer@example.com", "password": "super-secret-1"},
    )
    assert blocked_login.status_code == 403

    reactivate = client.patch(
        f"/api/admin/users/{customer_id}/status",
        json={"status": "active"},
        headers=_auth_headers(admin_token),
    )
    assert reactivate.status_code == 200
    assert reactivate.json()["status"] == "active"

    restored_login = client.post(
        "/api/auth/login",
        json={"emailAddress": "customer@example.com", "password": "super-secret-1"},
    )
    assert restored_login.status_code == 200


@pytest.mark.asyncio
async def test_admin_cannot_suspend_self(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    admin = _register(client, "admin@example.com")
    admin_id = admin["user"]["id"]
    await user_repository.update_role(UUID(admin_id), UserRole.ADMIN)
    admin_token = _login(client, "admin@example.com")["accessToken"]

    response = client.patch(
        f"/api/admin/users/{admin_id}/status",
        json={"status": "suspended"},
        headers=_auth_headers(admin_token),
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_admin_can_add_and_list_notes(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    admin = _register(client, "admin@example.com")
    await user_repository.update_role(UUID(admin["user"]["id"]), UserRole.ADMIN)
    admin_token = _login(client, "admin@example.com")["accessToken"]

    customer = _register(client, "customer@example.com")
    customer_id = customer["user"]["id"]

    add_response = client.post(
        f"/api/admin/users/{customer_id}/notes",
        json={"body": "Called about a quote."},
        headers=_auth_headers(admin_token),
    )
    assert add_response.status_code == 201
    assert add_response.json()["authorName"] == "Test User"

    list_response = client.get(
        f"/api/admin/users/{customer_id}/notes",
        headers=_auth_headers(admin_token),
    )
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["body"] == "Called about a quote."


@pytest.mark.asyncio
async def test_notes_for_unknown_user_return_404(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    admin = _register(client, "admin@example.com")
    await user_repository.update_role(UUID(admin["user"]["id"]), UserRole.ADMIN)
    admin_token = _login(client, "admin@example.com")["accessToken"]

    response = client.get(
        "/api/admin/users/11111111-1111-1111-1111-111111111111/notes",
        headers=_auth_headers(admin_token),
    )

    assert response.status_code == 404
