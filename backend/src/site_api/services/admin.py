from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from loguru import logger

from site_api.domain.account_notes import AccountNote, AccountNoteRepository
from site_api.domain.users import (
    AccountStatus,
    CannotModifySelfError,
    User,
    UserNotFoundError,
    UserRepository,
    UserRole,
)


@dataclass(frozen=True, slots=True)
class AddAccountNote:
    user_id: UUID
    author_id: UUID
    author_name: str
    body: str


class AdminService:
    def __init__(
        self,
        user_repository: UserRepository,
        note_repository: AccountNoteRepository,
        id_factory: Callable[[], UUID] = uuid4,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._users = user_repository
        self._notes = note_repository
        self._id_factory = id_factory
        self._clock = clock

    async def list_users(self) -> list[User]:
        return await self._users.list_all()

    async def update_role(self, user_id: UUID, role: UserRole, acting_admin_id: UUID) -> User:
        if user_id == acting_admin_id:
            raise CannotModifySelfError

        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError

        updated_user = await self._users.update_role(user_id, role)
        logger.bind(user_id=str(user_id), role=role.value).info("User role updated")
        return updated_user

    async def update_status(
        self, user_id: UUID, account_status: AccountStatus, acting_admin_id: UUID
    ) -> User:
        if user_id == acting_admin_id:
            raise CannotModifySelfError

        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError

        updated_user = await self._users.update_status(user_id, account_status)
        logger.bind(user_id=str(user_id), status=account_status.value).info(
            "User account status updated"
        )
        return updated_user

    async def list_notes(self, user_id: UUID) -> list[AccountNote]:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError

        return await self._notes.list_for_user(user_id)

    async def add_note(self, command: AddAccountNote) -> AccountNote:
        user = await self._users.get_by_id(command.user_id)
        if user is None:
            raise UserNotFoundError

        note = AccountNote(
            id=self._id_factory(),
            user_id=command.user_id,
            author_id=command.author_id,
            author_name=command.author_name,
            body=command.body,
            created_at=self._clock(),
        )
        saved_note = await self._notes.add(note)
        logger.bind(user_id=str(command.user_id)).info("Account note added")
        return saved_note
