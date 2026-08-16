from uuid import UUID

from fastapi.testclient import TestClient

from site_api.domain.users import UserRole
from tests.conftest import InMemoryAnalyticsRepository, InMemoryUserRepository


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


def test_track_page_view_returns_204(client: TestClient) -> None:
    response = client.post(
        "/api/analytics/pageview",
        json={"path": "/marketplace", "referrer": None, "sessionId": "session-1"},
    )

    assert response.status_code == 204


def test_track_click_returns_204(client: TestClient) -> None:
    response = client.post(
        "/api/analytics/click",
        json={
            "path": "/marketplace",
            "xPercent": 42.5,
            "yPercent": 88.0,
            "elementLabel": "Add to Cart",
            "sessionId": "session-1",
        },
    )

    assert response.status_code == 204


def test_track_click_rejects_out_of_range_position(client: TestClient) -> None:
    response = client.post(
        "/api/analytics/click",
        json={
            "path": "/marketplace",
            "xPercent": 150,
            "yPercent": 50,
            "elementLabel": None,
            "sessionId": "session-1",
        },
    )

    assert response.status_code == 422


def test_admin_pages_requires_admin(client: TestClient) -> None:
    user = _register(client, "client@example.com")

    response = client.get(
        "/api/admin/analytics/pages",
        headers=_auth_headers(user["accessToken"]),
    )

    assert response.status_code == 403


async def test_admin_pages_returns_tracked_views(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)

    client.post(
        "/api/analytics/pageview",
        json={"path": "/marketplace", "referrer": None, "sessionId": "session-1"},
    )
    client.post(
        "/api/analytics/pageview",
        json={"path": "/marketplace", "referrer": None, "sessionId": "session-2"},
    )

    response = client.get("/api/admin/analytics/pages", headers=_auth_headers(token))

    assert response.status_code == 200
    body = response.json()
    assert body[0]["path"] == "/marketplace"
    assert body[0]["viewCount"] == 2
    assert body[0]["uniqueSessions"] == 2


async def test_admin_heatmap_returns_click_points(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)

    client.post(
        "/api/analytics/click",
        json={
            "path": "/marketplace",
            "xPercent": 10,
            "yPercent": 20,
            "elementLabel": "Header",
            "sessionId": "session-1",
        },
    )

    response = client.get(
        "/api/admin/analytics/heatmap",
        params={"path": "/marketplace"},
        headers=_auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["elementLabel"] == "Header"


async def test_admin_heatmap_requires_admin(
    client: TestClient,
    analytics_repository: InMemoryAnalyticsRepository,
) -> None:
    user = _register(client, "client2@example.com")

    response = client.get(
        "/api/admin/analytics/heatmap",
        params={"path": "/marketplace"},
        headers=_auth_headers(user["accessToken"]),
    )

    assert response.status_code == 403
