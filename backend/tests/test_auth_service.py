from datetime import UTC, datetime
from uuid import UUID

import pytest

from site_api.domain.users import (
    AccountStatus,
    AccountSuspendedError,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    UserRole,
)
from site_api.services.auth import AuthenticateUser, AuthService, RegisterUser
from tests.conftest import InMemoryUserRepository


def _fake_hasher(password: str) -> str:
    return f"hashed:{password}"


def _fake_verifier(password: str, hashed_password: str) -> bool:
    return hashed_password == _fake_hasher(password)


@pytest.fixture
def service(user_repository: InMemoryUserRepository) -> AuthService:
    expected_id = UUID("9a53d09a-f258-4b09-9fb3-ef6df4c2f9fd")
    expected_time = datetime(2026, 8, 8, 12, 0, tzinfo=UTC)
    return AuthService(
        user_repository,
        id_factory=lambda: expected_id,
        clock=lambda: expected_time,
        password_hasher=_fake_hasher,
        password_verifier=_fake_verifier,
    )


@pytest.mark.asyncio
async def test_register_creates_customer_with_hashed_password(
    service: AuthService,
    user_repository: InMemoryUserRepository,
) -> None:
    user = await service.register(
        RegisterUser(
            email_address="taylor@example.com",
            full_name="Taylor Client",
            password="super-secret",
        )
    )

    assert user.email_address == "taylor@example.com"
    assert user.role is UserRole.CUSTOMER
    assert user.hashed_password == "hashed:super-secret"
    assert user_repository.users == [user]


@pytest.mark.asyncio
async def test_register_rejects_duplicate_email(
    service: AuthService,
) -> None:
    await service.register(
        RegisterUser(
            email_address="taylor@example.com",
            full_name="Taylor Client",
            password="super-secret",
        )
    )

    with pytest.raises(EmailAlreadyRegisteredError):
        await service.register(
            RegisterUser(
                email_address="taylor@example.com",
                full_name="Taylor Duplicate",
                password="another-secret",
            )
        )


@pytest.mark.asyncio
async def test_authenticate_returns_user_for_correct_password(
    service: AuthService,
) -> None:
    registered = await service.register(
        RegisterUser(
            email_address="taylor@example.com",
            full_name="Taylor Client",
            password="super-secret",
        )
    )

    authenticated = await service.authenticate(
        AuthenticateUser(email_address="taylor@example.com", password="super-secret")
    )

    assert authenticated.id == registered.id
    assert registered.last_login_at is None
    assert authenticated.last_login_at is not None


@pytest.mark.asyncio
async def test_authenticate_records_last_login_in_repository(
    service: AuthService,
    user_repository: InMemoryUserRepository,
) -> None:
    await service.register(
        RegisterUser(
            email_address="taylor@example.com",
            full_name="Taylor Client",
            password="super-secret",
        )
    )

    await service.authenticate(
        AuthenticateUser(email_address="taylor@example.com", password="super-secret")
    )

    stored_user = await user_repository.get_by_email("taylor@example.com")
    assert stored_user is not None
    assert stored_user.last_login_at is not None


@pytest.mark.asyncio
async def test_authenticate_rejects_suspended_account(
    service: AuthService,
    user_repository: InMemoryUserRepository,
) -> None:
    registered = await service.register(
        RegisterUser(
            email_address="taylor@example.com",
            full_name="Taylor Client",
            password="super-secret",
        )
    )
    await user_repository.update_status(registered.id, AccountStatus.SUSPENDED)

    with pytest.raises(AccountSuspendedError):
        await service.authenticate(
            AuthenticateUser(email_address="taylor@example.com", password="super-secret")
        )


@pytest.mark.asyncio
async def test_authenticate_rejects_unknown_email(service: AuthService) -> None:
    with pytest.raises(InvalidCredentialsError):
        await service.authenticate(
            AuthenticateUser(email_address="nobody@example.com", password="whatever")
        )


@pytest.mark.asyncio
async def test_authenticate_rejects_incorrect_password(service: AuthService) -> None:
    await service.register(
        RegisterUser(
            email_address="taylor@example.com",
            full_name="Taylor Client",
            password="super-secret",
        )
    )

    with pytest.raises(InvalidCredentialsError):
        await service.authenticate(
            AuthenticateUser(email_address="taylor@example.com", password="wrong-password")
        )
