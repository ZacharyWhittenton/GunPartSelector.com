from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient

from site_api.domain.testimonials import Testimonial, TestimonialStatus
from tests.conftest import InMemoryTestimonialRepository


def _register(client: TestClient, email: str, full_name: str = "Test User") -> dict:
    response = client.post(
        "/api/auth/register",
        json={"emailAddress": email, "fullName": full_name, "password": "super-secret-1"},
    )
    assert response.status_code == 201
    return response.json()


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _make_testimonial(**overrides: object) -> Testimonial:
    now = datetime.now(UTC)
    defaults: dict[str, object] = {
        "id": UUID(int=1),
        "customer_id": None,
        "customer_name": "Priya Anand",
        "rating": 5,
        "body": "Great experience overall.",
        "status": TestimonialStatus.APPROVED,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return Testimonial(**defaults)


def test_list_approved_testimonials_is_public_and_excludes_pending(
    client: TestClient,
    testimonial_repository: InMemoryTestimonialRepository,
) -> None:
    testimonial_repository.testimonials.append(_make_testimonial())
    testimonial_repository.testimonials.append(
        _make_testimonial(id=UUID(int=2), status=TestimonialStatus.PENDING)
    )

    response = client.get("/api/testimonials")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["customerName"] == "Priya Anand"
    assert "status" not in body[0]


def test_list_approved_testimonials_respects_limit(
    client: TestClient,
    testimonial_repository: InMemoryTestimonialRepository,
) -> None:
    for index in range(3):
        testimonial_repository.testimonials.append(_make_testimonial(id=UUID(int=index + 1)))

    response = client.get("/api/testimonials?limit=2")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_my_testimonial_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/testimonials/mine")

    assert response.status_code == 401


def test_get_my_testimonial_returns_null_when_none_submitted(client: TestClient) -> None:
    user = _register(client, "customer@example.com")

    response = client.get(
        "/api/testimonials/mine",
        headers=_auth_headers(user["accessToken"]),
    )

    assert response.status_code == 200
    assert response.json() is None


def test_submit_testimonial_requires_authentication(client: TestClient) -> None:
    response = client.post(
        "/api/testimonials/mine",
        json={"rating": 5, "body": "Loved it."},
    )

    assert response.status_code == 401


def test_submit_testimonial_success_starts_pending(client: TestClient) -> None:
    user = _register(client, "customer@example.com", "Jamie Client")
    headers = _auth_headers(user["accessToken"])

    response = client.post(
        "/api/testimonials/mine",
        json={"rating": 5, "body": "Loved the whole process."},
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["customerName"] == "Jamie Client"

    mine_response = client.get("/api/testimonials/mine", headers=headers)
    assert mine_response.json()["id"] == body["id"]


def test_submit_testimonial_rejects_invalid_rating(client: TestClient) -> None:
    user = _register(client, "customer@example.com")

    response = client.post(
        "/api/testimonials/mine",
        json={"rating": 7, "body": "Too enthusiastic."},
        headers=_auth_headers(user["accessToken"]),
    )

    assert response.status_code == 422


def test_resubmitting_replaces_previous_and_stays_hidden_from_public_list(
    client: TestClient,
    testimonial_repository: InMemoryTestimonialRepository,
) -> None:
    user = _register(client, "customer@example.com")
    headers = _auth_headers(user["accessToken"])

    first = client.post(
        "/api/testimonials/mine",
        json={"rating": 3, "body": "It was fine."},
        headers=headers,
    ).json()

    second = client.post(
        "/api/testimonials/mine",
        json={"rating": 5, "body": "Actually, it was great."},
        headers=headers,
    ).json()

    assert first["id"] == second["id"]
    assert second["rating"] == 5
    assert len(testimonial_repository.testimonials) == 1
    assert client.get("/api/testimonials").json() == []
