from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from site_api.api.dependencies import get_settings
from site_api.core.config import Settings
from site_api.domain.users import AccountStatus
from tests.conftest import InMemoryUserRepository


def _register(client: TestClient, email: str = "taylor@example.com") -> dict:
    response = client.post(
        "/api/auth/register",
        json={
            "emailAddress": email,
            "fullName": "Taylor Client",
            "password": "super-secret-1",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_register_creates_customer_account(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    body = _register(client)

    assert body["tokenType"] == "bearer"
    assert body["accessToken"]
    assert body["user"]["emailAddress"] == "taylor@example.com"
    assert body["user"]["role"] == "customer"
    assert len(user_repository.users) == 1


def test_register_rejects_duplicate_email(client: TestClient) -> None:
    _register(client)

    response = client.post(
        "/api/auth/register",
        json={
            "emailAddress": "taylor@example.com",
            "fullName": "Taylor Duplicate",
            "password": "another-secret-1",
        },
    )

    assert response.status_code == 409


def test_register_rejects_short_password(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "emailAddress": "taylor@example.com",
            "fullName": "Taylor Client",
            "password": "short",
        },
    )

    assert response.status_code == 422


def test_login_succeeds_with_correct_credentials(client: TestClient) -> None:
    _register(client)

    response = client.post(
        "/api/auth/login",
        json={"emailAddress": "taylor@example.com", "password": "super-secret-1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["emailAddress"] == "taylor@example.com"
    assert body["accessToken"]


def test_login_rejects_incorrect_password(client: TestClient) -> None:
    _register(client)

    response = client.post(
        "/api/auth/login",
        json={"emailAddress": "taylor@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401


def test_login_rejects_unknown_email(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"emailAddress": "nobody@example.com", "password": "whatever-1"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_rejects_suspended_account(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    registered = _register(client)
    await user_repository.update_status(UUID(registered["user"]["id"]), AccountStatus.SUSPENDED)

    response = client.post(
        "/api/auth/login",
        json={"emailAddress": "taylor@example.com", "password": "super-secret-1"},
    )

    assert response.status_code == 403


def test_me_returns_current_user_for_valid_token(client: TestClient) -> None:
    registered = _register(client)

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {registered['accessToken']}"},
    )

    assert response.status_code == 200
    assert response.json()["emailAddress"] == "taylor@example.com"


def test_me_rejects_missing_token(client: TestClient) -> None:
    response = client.get("/api/auth/me")

    assert response.status_code == 401


def test_me_rejects_invalid_token(client: TestClient) -> None:
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer not-a-real-token"},
    )

    assert response.status_code == 401


def test_dev_login_signs_in_as_seeded_admin(client: TestClient) -> None:
    _register(client, email="admin@example.com")

    response = client.post("/api/auth/dev-login", json={"role": "admin"})

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["emailAddress"] == "admin@example.com"
    assert body["accessToken"]


def test_dev_login_signs_in_as_seeded_customer(client: TestClient) -> None:
    _register(client, email="morgan.rivera@example.com")

    response = client.post("/api/auth/dev-login", json={"role": "customer"})

    assert response.status_code == 200
    assert response.json()["user"]["emailAddress"] == "morgan.rivera@example.com"


def test_dev_login_returns_404_when_seed_account_missing(client: TestClient) -> None:
    response = client.post("/api/auth/dev-login", json={"role": "admin"})

    assert response.status_code == 404


def test_dev_login_returns_404_in_production(client: TestClient, app: FastAPI) -> None:
    _register(client, email="admin@example.com")
    app.dependency_overrides[get_settings] = lambda: Settings(
        environment="production", jwt_secret_key="a-real-secret-key-not-the-default"
    )

    try:
        response = client.post("/api/auth/dev-login", json={"role": "admin"})
        assert response.status_code == 404
    finally:
        del app.dependency_overrides[get_settings]
