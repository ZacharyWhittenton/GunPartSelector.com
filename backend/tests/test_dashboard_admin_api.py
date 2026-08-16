from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient

from site_api.domain.testimonials import Testimonial, TestimonialStatus
from site_api.domain.users import UserRole
from tests.conftest import InMemoryTestimonialRepository, InMemoryUserRepository


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


def test_dashboard_summary_requires_admin(client: TestClient) -> None:
    user = _register(client, "client@example.com")

    response = client.get(
        "/api/admin/dashboard/summary",
        headers=_auth_headers(user["accessToken"]),
    )

    assert response.status_code == 403


async def test_dashboard_summary_shape_and_values(
    client: TestClient,
    user_repository: InMemoryUserRepository,
    testimonial_repository: InMemoryTestimonialRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)
    now = datetime.now(UTC)
    testimonial_repository.testimonials.append(
        Testimonial(
            id=UUID(int=1),
            customer_id=None,
            customer_name="Priya Anand",
            rating=5,
            body="Great work.",
            status=TestimonialStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
    )

    response = client.get("/api/admin/dashboard/summary", headers=_auth_headers(token))

    assert response.status_code == 200
    body = response.json()
    assert body["pendingTestimonials"] == 1
    assert body["newLeadsToday"] == 0
    assert body["upcomingAppointments"] == 0
    assert body["revenueThisWeekCents"] == 0
    assert body["revenueThisMonthCents"] == 0
    assert body["recentActivity"] == []
