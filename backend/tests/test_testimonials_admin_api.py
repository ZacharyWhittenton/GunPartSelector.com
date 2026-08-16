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


def _make_testimonial(**overrides: object) -> Testimonial:
    now = datetime.now(UTC)
    defaults: dict[str, object] = {
        "id": UUID(int=1),
        "customer_id": None,
        "customer_name": "Priya Anand",
        "rating": 5,
        "body": "Great experience overall.",
        "status": TestimonialStatus.PENDING,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return Testimonial(**defaults)


def test_list_all_testimonials_requires_admin(client: TestClient) -> None:
    user = _register(client, "client@example.com")

    response = client.get(
        "/api/admin/testimonials",
        headers=_auth_headers(user["accessToken"]),
    )

    assert response.status_code == 403


async def test_list_all_testimonials_filters_by_status(
    client: TestClient,
    user_repository: InMemoryUserRepository,
    testimonial_repository: InMemoryTestimonialRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)
    testimonial_repository.testimonials.append(_make_testimonial())
    testimonial_repository.testimonials.append(
        _make_testimonial(id=UUID(int=2), status=TestimonialStatus.APPROVED)
    )

    pending_response = client.get(
        "/api/admin/testimonials?status=pending",
        headers=_auth_headers(token),
    )
    assert pending_response.status_code == 200
    assert len(pending_response.json()) == 1

    all_response = client.get(
        "/api/admin/testimonials",
        headers=_auth_headers(token),
    )
    assert len(all_response.json()) == 2


async def test_approve_testimonial(
    client: TestClient,
    user_repository: InMemoryUserRepository,
    testimonial_repository: InMemoryTestimonialRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)
    testimonial_repository.testimonials.append(_make_testimonial())

    response = client.post(
        f"/api/admin/testimonials/{UUID(int=1)}/approve",
        headers=_auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"


async def test_approve_testimonial_404_when_missing(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)

    response = client.post(
        f"/api/admin/testimonials/{UUID(int=999)}/approve",
        headers=_auth_headers(token),
    )

    assert response.status_code == 404


async def test_reject_testimonial(
    client: TestClient,
    user_repository: InMemoryUserRepository,
    testimonial_repository: InMemoryTestimonialRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)
    testimonial_repository.testimonials.append(_make_testimonial())

    response = client.post(
        f"/api/admin/testimonials/{UUID(int=1)}/reject",
        headers=_auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


async def test_reject_testimonial_404_when_missing(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)

    response = client.post(
        f"/api/admin/testimonials/{UUID(int=999)}/reject",
        headers=_auth_headers(token),
    )

    assert response.status_code == 404


async def test_delete_testimonial(
    client: TestClient,
    user_repository: InMemoryUserRepository,
    testimonial_repository: InMemoryTestimonialRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)
    testimonial_repository.testimonials.append(_make_testimonial())

    response = client.delete(
        f"/api/admin/testimonials/{UUID(int=1)}",
        headers=_auth_headers(token),
    )

    assert response.status_code == 204
    assert testimonial_repository.testimonials == []


async def test_delete_testimonial_404_when_missing(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)

    response = client.delete(
        f"/api/admin/testimonials/{UUID(int=999)}",
        headers=_auth_headers(token),
    )

    assert response.status_code == 404
