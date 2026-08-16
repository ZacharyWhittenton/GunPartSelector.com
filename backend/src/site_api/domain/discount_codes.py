from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID


class DiscountType(StrEnum):
    PERCENT = "percent"
    FIXED = "fixed"


@dataclass(frozen=True, slots=True)
class DiscountCode:
    id: UUID
    code: str
    discount_type: DiscountType
    value: int
    is_active: bool
    expires_at: datetime | None
    max_redemptions: int | None
    redemption_count: int
    created_at: datetime
    updated_at: datetime


class DiscountCodeNotFoundError(Exception):
    """Raised when a referenced discount code does not exist."""


class DuplicateDiscountCodeError(Exception):
    """Raised when creating a discount code whose code already exists."""


class DiscountCodeInvalidError(Exception):
    """Raised when a code is invalid: bad value, inactive, expired, or exhausted."""


class DiscountCodeRepository(Protocol):
    async def add(self, discount_code: DiscountCode) -> DiscountCode: ...

    async def update(self, discount_code: DiscountCode) -> DiscountCode: ...

    async def delete(self, discount_code_id: UUID) -> None: ...

    async def get_by_id(self, discount_code_id: UUID) -> DiscountCode | None: ...

    async def get_by_code(self, code: str) -> DiscountCode | None: ...

    async def list_all(self) -> list[DiscountCode]: ...
