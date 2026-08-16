from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID


class UserRole(StrEnum):
    ADMIN = "admin"
    CUSTOMER = "customer"
    GUEST = "guest"


class AccountStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


@dataclass(frozen=True, slots=True)
class User:
    id: UUID
    email_address: str
    full_name: str
    hashed_password: str
    role: UserRole
    status: AccountStatus
    created_at: datetime
    last_login_at: datetime | None


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """The identity carried by a verified access token, without touching the database."""

    id: UUID
    email_address: str
    full_name: str
    role: UserRole


class EmailAlreadyRegisteredError(Exception):
    """Raised when registering an email address that already has an account."""


class InvalidCredentialsError(Exception):
    """Raised when login credentials do not match a known, active account."""


class AccountSuspendedError(Exception):
    """Raised when a suspended account's credentials would otherwise be valid."""


class UserNotFoundError(Exception):
    """Raised when an operation references a user id that does not exist."""


class CannotModifySelfError(Exception):
    """Raised when an admin tries to change their own role or account status."""


class UserRepository(Protocol):
    async def add(self, user: User) -> User: ...

    async def get_by_email(self, email_address: str) -> User | None: ...

    async def get_by_id(self, user_id: UUID) -> User | None: ...

    async def list_all(self) -> list[User]: ...

    async def update_role(self, user_id: UUID, role: UserRole) -> User: ...

    async def update_status(self, user_id: UUID, status: AccountStatus) -> User: ...

    async def update_last_login(self, user_id: UUID, when: datetime) -> None: ...
