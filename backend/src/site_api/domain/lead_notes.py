from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class LeadNote:
    id: UUID
    lead_id: UUID
    author_id: UUID
    author_name: str
    body: str
    created_at: datetime


class LeadNoteRepository(Protocol):
    async def add(self, note: LeadNote) -> LeadNote: ...

    async def list_for_lead(self, lead_id: UUID) -> list[LeadNote]: ...
