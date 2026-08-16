from fastapi.testclient import TestClient

from site_api.core.config import Settings
from site_api.main import create_app
from tests.conftest import InMemoryContactRequestRepository


def test_health_does_not_require_database(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}


def test_submit_contact_request(
    client: TestClient,
    repository: InMemoryContactRequestRepository,
) -> None:
    response = client.post(
        "/api/contact-requests",
        json={
            "name": "Taylor Client",
            "emailAddress": "taylor@example.com",
            "company": "Example Property Management",
            "phone": "512-555-0100",
            "service": "Parking Lot Striping",
            "message": "Please provide an estimate.",
        },
    )

    assert response.status_code == 202
    assert response.json()["status"] == "received"
    assert len(repository.contact_requests) == 1
    assert repository.contact_requests[0].email_address == "taylor@example.com"


def test_rejects_invalid_contact_request(client: TestClient) -> None:
    response = client.post(
        "/api/contact-requests",
        json={
            "name": "Taylor Client",
            "emailAddress": "not-an-email",
            "service": "Parking Lot Striping",
            "message": "Please provide an estimate.",
        },
    )

    assert response.status_code == 422


def test_contact_endpoint_reports_missing_database_configuration() -> None:
    app = create_app(Settings(environment="test", cors_origins=[], database_url=None))

    with TestClient(app) as client:
        response = client.post(
            "/api/contact-requests",
            json={
                "name": "Taylor Client",
                "emailAddress": "taylor@example.com",
                "service": "Parking Lot Striping",
                "message": "Please provide an estimate.",
            },
        )

    assert response.status_code == 503
    assert response.json() == {"detail": "Database is not configured"}
