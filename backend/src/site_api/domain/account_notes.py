from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AccountNote:
    id: UUID
    user_id: UUID
    author_id: UUID
    author_name: str
    body: str
    created_at: datetime


class AccountNoteRepository(Protocol):
    async def add(self, note: AccountNote) -> AccountNote: ...

    async def list_for_user(self, user_id: UUID) -> list[AccountNote]: ...
