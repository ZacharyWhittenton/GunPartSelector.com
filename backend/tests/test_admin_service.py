from datetime import UTC, datetime
from uuid import UUID

import pytest

from site_api.domain.users import (
    AccountStatus,
    CannotModifySelfError,
    User,
    UserNotFoundError,
    UserRole,
)
from site_api.services.admin import AddAccountNote, AdminService
from tests.conftest import InMemoryAccountNoteRepository, InMemoryUserRepository


def _make_user(**overrides: object) -> User:
    defaults: dict[str, object] = {
        "id": UUID("9a53d09a-f258-4b09-9fb3-ef6df4c2f9fd"),
        "email_address": "taylor@example.com",
        "full_name": "Taylor Client",
        "hashed_password": "hashed-password",
        "role": UserRole.CUSTOMER,
        "status": AccountStatus.ACTIVE,
        "created_at": datetime(2026, 8, 8, 12, 0, tzinfo=UTC),
        "last_login_at": None,
    }
    defaults.update(overrides)
    return User(**defaults)


@pytest.fixture
def service(
    user_repository: InMemoryUserRepository,
    note_repository: InMemoryAccountNoteRepository,
) -> AdminService:
    expected_id = UUID("33333333-3333-3333-3333-333333333333")
    expected_time = datetime(2026, 8, 8, 14, 0, tzinfo=UTC)
    return AdminService(
        user_repository,
        note_repository,
        id_factory=lambda: expected_id,
        clock=lambda: expected_time,
    )


@pytest.mark.asyncio
async def test_list_users_returns_everyone(
    service: AdminService,
    user_repository: InMemoryUserRepository,
) -> None:
    await user_repository.add(_make_user())

    users = await service.list_users()

    assert len(users) == 1


@pytest.mark.asyncio
async def test_update_role_promotes_user(
    service: AdminService,
    user_repository: InMemoryUserRepository,
) -> None:
    target = await user_repository.add(_make_user())
    admin_id = UUID("22222222-2222-2222-2222-222222222222")

    updated = await service.update_role(target.id, UserRole.ADMIN, admin_id)

    assert updated.role is UserRole.ADMIN


@pytest.mark.asyncio
async def test_update_role_rejects_self_modification(service: AdminService) -> None:
    admin_id = UUID("9a53d09a-f258-4b09-9fb3-ef6df4c2f9fd")

    with pytest.raises(CannotModifySelfError):
        await service.update_role(admin_id, UserRole.CUSTOMER, admin_id)


@pytest.mark.asyncio
async def test_update_role_raises_when_user_missing(service: AdminService) -> None:
    with pytest.raises(UserNotFoundError):
        await service.update_role(
            UUID("11111111-1111-1111-1111-111111111111"),
            UserRole.ADMIN,
            UUID("22222222-2222-2222-2222-222222222222"),
        )


@pytest.mark.asyncio
async def test_update_status_suspends_user(
    service: AdminService,
    user_repository: InMemoryUserRepository,
) -> None:
    target = await user_repository.add(_make_user())
    admin_id = UUID("22222222-2222-2222-2222-222222222222")

    updated = await service.update_status(target.id, AccountStatus.SUSPENDED, admin_id)

    assert updated.status is AccountStatus.SUSPENDED


@pytest.mark.asyncio
async def test_update_status_rejects_self_modification(service: AdminService) -> None:
    admin_id = UUID("9a53d09a-f258-4b09-9fb3-ef6df4c2f9fd")

    with pytest.raises(CannotModifySelfError):
        await service.update_status(admin_id, AccountStatus.SUSPENDED, admin_id)


@pytest.mark.asyncio
async def test_add_note_and_list_notes(
    service: AdminService,
    user_repository: InMemoryUserRepository,
) -> None:
    target = await user_repository.add(_make_user())
    admin_id = UUID("22222222-2222-2222-2222-222222222222")

    note = await service.add_note(
        AddAccountNote(
            user_id=target.id,
            author_id=admin_id,
            author_name="Admin Person",
            body="Called about a quote.",
        )
    )

    assert note.body == "Called about a quote."
    assert note.author_name == "Admin Person"

    notes = await service.list_notes(target.id)
    assert notes == [note]


@pytest.mark.asyncio
async def test_add_note_raises_when_user_missing(service: AdminService) -> None:
    with pytest.raises(UserNotFoundError):
        await service.add_note(
            AddAccountNote(
                user_id=UUID("11111111-1111-1111-1111-111111111111"),
                author_id=UUID("22222222-2222-2222-2222-222222222222"),
                author_name="Admin Person",
                body="Note",
            )
        )


@pytest.mark.asyncio
async def test_list_notes_raises_when_user_missing(service: AdminService) -> None:
    with pytest.raises(UserNotFoundError):
        await service.list_notes(UUID("11111111-1111-1111-1111-111111111111"))
