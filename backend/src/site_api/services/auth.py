from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from loguru import logger

from site_api.core.security import hash_password, verify_password
from site_api.domain.users import (
    AccountStatus,
    AccountSuspendedError,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    User,
    UserRepository,
    UserRole,
)


@dataclass(frozen=True, slots=True)
class RegisterUser:
    email_address: str
    full_name: str
    password: str


@dataclass(frozen=True, slots=True)
class AuthenticateUser:
    email_address: str
    password: str


class AuthService:
    def __init__(
        self,
        repository: UserRepository,
        id_factory: Callable[[], UUID] = uuid4,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        password_hasher: Callable[[str], str] = hash_password,
        password_verifier: Callable[[str, str], bool] = verify_password,
    ) -> None:
        self._repository = repository
        self._id_factory = id_factory
        self._clock = clock
        self._password_hasher = password_hasher
        self._password_verifier = password_verifier

    async def register(self, command: RegisterUser) -> User:
        existing_user = await self._repository.get_by_email(command.email_address)
        if existing_user is not None:
            raise EmailAlreadyRegisteredError

        user = User(
            id=self._id_factory(),
            email_address=command.email_address,
            full_name=command.full_name,
            hashed_password=self._password_hasher(command.password),
            role=UserRole.CUSTOMER,
            status=AccountStatus.ACTIVE,
            created_at=self._clock(),
            last_login_at=None,
        )
        saved_user = await self._repository.add(user)
        logger.bind(user_id=str(saved_user.id)).info("User registered")
        return saved_user

    async def authenticate(self, command: AuthenticateUser) -> User:
        user = await self._repository.get_by_email(command.email_address)
        if user is None or not self._password_verifier(command.password, user.hashed_password):
            raise InvalidCredentialsError

        if user.status is AccountStatus.SUSPENDED:
            raise AccountSuspendedError

        login_time = self._clock()
        await self._repository.update_last_login(user.id, login_time)
        logger.bind(user_id=str(user.id)).info("User authenticated")
        return replace(user, last_login_at=login_time)
