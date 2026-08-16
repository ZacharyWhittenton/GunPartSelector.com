from uuid import UUID

from fastapi.testclient import TestClient

from site_api.domain.users import UserRole
from tests.conftest import InMemoryUserRepository

_LEAD_PAYLOAD = {
    "name": "Taylor Client",
    "emailAddress": "taylor@example.com",
    "company": None,
    "phone": None,
    "service": "Website Redesign",
    "message": "Please call me.",
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


def _submit_lead(client: TestClient) -> str:
    response = client.post("/api/contact-requests", json=_LEAD_PAYLOAD)
    assert response.status_code == 202
    return response.json()["id"]


def test_list_leads_requires_admin(client: TestClient) -> None:
    user = _register(client, "client@example.com")

    response = client.get(
        "/api/admin/contact-requests",
        headers=_auth_headers(user["accessToken"]),
    )

    assert response.status_code == 403


async def test_list_leads_shows_new_submission(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)
    _submit_lead(client)

    response = client.get("/api/admin/contact-requests", headers=_auth_headers(token))

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["status"] == "received"
    assert body[0]["name"] == "Taylor Client"


async def test_list_leads_filters_by_status(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)
    lead_id = _submit_lead(client)
    client.patch(
        f"/api/admin/contact-requests/{lead_id}/status",
        json={"status": "contacted"},
        headers=_auth_headers(token),
    )

    received_response = client.get(
        "/api/admin/contact-requests?status=received", headers=_auth_headers(token)
    )
    contacted_response = client.get(
        "/api/admin/contact-requests?status=contacted", headers=_auth_headers(token)
    )

    assert received_response.json() == []
    assert len(contacted_response.json()) == 1


async def test_update_lead_status_success(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)
    lead_id = _submit_lead(client)

    response = client.patch(
        f"/api/admin/contact-requests/{lead_id}/status",
        json={"status": "qualified"},
        headers=_auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "qualified"


async def test_update_lead_status_404_when_missing(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)

    response = client.patch(
        f"/api/admin/contact-requests/{UUID(int=999)}/status",
        json={"status": "won"},
        headers=_auth_headers(token),
    )

    assert response.status_code == 404


async def test_update_lead_status_rejects_invalid_status(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)
    lead_id = _submit_lead(client)

    response = client.patch(
        f"/api/admin/contact-requests/{lead_id}/status",
        json={"status": "not-a-real-status"},
        headers=_auth_headers(token),
    )

    assert response.status_code == 422


def test_list_lead_notes_requires_admin(client: TestClient) -> None:
    user = _register(client, "client@example.com")

    response = client.get(
        f"/api/admin/contact-requests/{UUID(int=1)}/notes",
        headers=_auth_headers(user["accessToken"]),
    )

    assert response.status_code == 403


async def test_add_and_list_lead_notes(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)
    lead_id = _submit_lead(client)

    add_response = client.post(
        f"/api/admin/contact-requests/{lead_id}/notes",
        json={"body": "Called, left a voicemail."},
        headers=_auth_headers(token),
    )
    assert add_response.status_code == 201
    assert add_response.json()["authorName"] == "Admin Person"

    list_response = client.get(
        f"/api/admin/contact-requests/{lead_id}/notes",
        headers=_auth_headers(token),
    )
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["body"] == "Called, left a voicemail."


async def test_add_lead_note_404_when_lead_missing(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)

    response = client.post(
        f"/api/admin/contact-requests/{UUID(int=999)}/notes",
        json={"body": "Note body"},
        headers=_auth_headers(token),
    )

    assert response.status_code == 404


async def test_list_lead_notes_404_when_lead_missing(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)

    response = client.get(
        f"/api/admin/contact-requests/{UUID(int=999)}/notes",
        headers=_auth_headers(token),
    )

    assert response.status_code == 404


async def test_update_lead_follow_up_success(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)
    lead_id = _submit_lead(client)

    response = client.patch(
        f"/api/admin/contact-requests/{lead_id}/follow-up",
        json={"followUpAt": "2026-08-15T09:00:00Z"},
        headers=_auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["followUpAt"] is not None


async def test_update_lead_follow_up_can_clear(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)
    lead_id = _submit_lead(client)
    client.patch(
        f"/api/admin/contact-requests/{lead_id}/follow-up",
        json={"followUpAt": "2026-08-15T09:00:00Z"},
        headers=_auth_headers(token),
    )

    response = client.patch(
        f"/api/admin/contact-requests/{lead_id}/follow-up",
        json={"followUpAt": None},
        headers=_auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["followUpAt"] is None


async def test_update_lead_follow_up_404_when_missing(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)

    response = client.patch(
        f"/api/admin/contact-requests/{UUID(int=999)}/follow-up",
        json={"followUpAt": "2026-08-15T09:00:00Z"},
        headers=_auth_headers(token),
    )

    assert response.status_code == 404
