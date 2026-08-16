from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID


class TestimonialStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class Testimonial:
    id: UUID
    customer_id: UUID | None
    customer_name: str
    rating: int
    body: str
    status: TestimonialStatus
    created_at: datetime
    updated_at: datetime


class TestimonialNotFoundError(Exception):
    """Raised when a referenced testimonial does not exist."""


class InvalidRatingError(Exception):
    """Raised when a testimonial rating is outside the 1-5 range."""


class TestimonialRepository(Protocol):
    async def add(self, testimonial: Testimonial) -> Testimonial: ...

    async def update(self, testimonial: Testimonial) -> Testimonial: ...

    async def delete(self, testimonial_id: UUID) -> None: ...

    async def get_by_id(self, testimonial_id: UUID) -> Testimonial | None: ...

    async def get_by_customer_id(self, customer_id: UUID) -> Testimonial | None: ...

    async def list_approved(self, limit: int | None = None) -> list[Testimonial]: ...

    async def list_all(self, status: TestimonialStatus | None = None) -> list[Testimonial]: ...
