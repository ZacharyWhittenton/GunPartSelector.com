from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from site_api.domain.scheduling import Appointment, AppointmentStatus
from site_api.domain.users import UserRole
from tests.conftest import InMemoryAppointmentRepository, InMemoryUserRepository

ADMIN_SEED_ID = UUID("11111111-1111-1111-1111-111111111111")


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


def _make_slot(**overrides: object) -> Appointment:
    now = datetime.now(UTC)
    defaults: dict[str, object] = {
        "id": UUID(int=1),
        "starts_at": now + timedelta(days=1),
        "ends_at": now + timedelta(days=1, hours=1),
        "status": AppointmentStatus.OPEN,
        "client_id": None,
        "client_name": None,
        "client_email": None,
        "notes": None,
        "created_by_admin_id": ADMIN_SEED_ID,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return Appointment(**defaults)


def test_list_open_slots_is_public_and_omits_client_details(
    client: TestClient,
    appointment_repository: InMemoryAppointmentRepository,
) -> None:
    appointment_repository.appointments.append(_make_slot())

    response = client.get("/api/scheduling/slots")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert "clientName" not in body[0]
    assert "status" not in body[0]


def test_book_slot_requires_authentication(
    client: TestClient,
    appointment_repository: InMemoryAppointmentRepository,
) -> None:
    appointment_repository.appointments.append(_make_slot())

    response = client.post(f"/api/scheduling/slots/{UUID(int=1)}/book", json={})

    assert response.status_code == 401


def test_book_slot_success_as_authenticated_client(
    client: TestClient,
    appointment_repository: InMemoryAppointmentRepository,
) -> None:
    appointment_repository.appointments.append(_make_slot())
    user = _register(client, "client@example.com", "Taylor Client")
    token = user["accessToken"]

    response = client.post(
        f"/api/scheduling/slots/{UUID(int=1)}/book",
        json={"notes": "Looking forward to it"},
        headers=_auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "booked"
    assert body["clientId"] == user["user"]["id"]
    assert body["notes"] == "Looking forward to it"


def test_book_slot_conflict_when_already_booked(
    client: TestClient,
    appointment_repository: InMemoryAppointmentRepository,
) -> None:
    appointment_repository.appointments.append(
        _make_slot(status=AppointmentStatus.BOOKED, client_id=UUID(int=99))
    )
    user = _register(client, "client@example.com")

    response = client.post(
        f"/api/scheduling/slots/{UUID(int=1)}/book",
        json={},
        headers=_auth_headers(user["accessToken"]),
    )

    assert response.status_code == 409


def test_list_my_appointments_returns_only_own_bookings(
    client: TestClient,
    appointment_repository: InMemoryAppointmentRepository,
) -> None:
    owner = _register(client, "owner@example.com")
    other = _register(client, "other@example.com")
    appointment_repository.appointments.append(
        _make_slot(status=AppointmentStatus.BOOKED, client_id=UUID(owner["user"]["id"]))
    )

    response = client.get(
        "/api/scheduling/appointments/mine",
        headers=_auth_headers(other["accessToken"]),
    )

    assert response.status_code == 200
    assert response.json() == []


def test_cancel_appointment_forbidden_for_non_owner(
    client: TestClient,
    appointment_repository: InMemoryAppointmentRepository,
) -> None:
    owner = _register(client, "owner@example.com")
    other = _register(client, "other@example.com")
    appointment_repository.appointments.append(
        _make_slot(status=AppointmentStatus.BOOKED, client_id=UUID(owner["user"]["id"]))
    )

    response = client.post(
        f"/api/scheduling/appointments/{UUID(int=1)}/cancel",
        headers=_auth_headers(other["accessToken"]),
    )

    assert response.status_code == 403


def test_admin_create_slot_requires_admin(client: TestClient) -> None:
    user = _register(client, "client@example.com")
    now = datetime.now(UTC)

    response = client.post(
        "/api/admin/scheduling/slots",
        json={
            "startsAt": (now + timedelta(days=1)).isoformat(),
            "endsAt": (now + timedelta(days=1, hours=1)).isoformat(),
        },
        headers=_auth_headers(user["accessToken"]),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_create_and_list_appointments(
    client: TestClient,
    user_repository: InMemoryUserRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)
    now = datetime.now(UTC)

    create_response = client.post(
        "/api/admin/scheduling/slots",
        json={
            "startsAt": (now + timedelta(days=1)).isoformat(),
            "endsAt": (now + timedelta(days=1, hours=1)).isoformat(),
        },
        headers=_auth_headers(token),
    )
    assert create_response.status_code == 201
    assert create_response.json()["status"] == "open"

    list_response = client.get(
        "/api/admin/scheduling/appointments?status=open",
        headers=_auth_headers(token),
    )
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


@pytest.mark.asyncio
async def test_admin_delete_slot_rejects_when_booked(
    client: TestClient,
    appointment_repository: InMemoryAppointmentRepository,
    user_repository: InMemoryUserRepository,
) -> None:
    token = await _make_admin_token(client, user_repository)
    appointment_repository.appointments.append(
        _make_slot(status=AppointmentStatus.BOOKED, client_id=UUID(int=99))
    )

    response = client.delete(
        f"/api/admin/scheduling/slots/{UUID(int=1)}",
        headers=_auth_headers(token),
    )

    assert response.status_code == 409
