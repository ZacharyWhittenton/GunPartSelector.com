from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from loguru import logger

from site_api.domain.discount_codes import (
    DiscountCode,
    DiscountCodeInvalidError,
    DiscountCodeNotFoundError,
    DiscountCodeRepository,
    DiscountType,
    DuplicateDiscountCodeError,
)

MAX_PERCENT_VALUE = 100


@dataclass(frozen=True, slots=True)
class CreateDiscountCode:
    code: str
    discount_type: DiscountType
    value: int
    expires_at: datetime | None
    max_redemptions: int | None


@dataclass(frozen=True, slots=True)
class UpdateDiscountCode:
    discount_type: DiscountType
    value: int
    expires_at: datetime | None
    max_redemptions: int | None


def _normalize_code(code: str) -> str:
    return code.strip().upper()


def _validate_value(discount_type: DiscountType, value: int) -> None:
    if value <= 0:
        raise DiscountCodeInvalidError
    if discount_type is DiscountType.PERCENT and value > MAX_PERCENT_VALUE:
        raise DiscountCodeInvalidError


class DiscountCodeService:
    def __init__(
        self,
        repository: DiscountCodeRepository,
        id_factory: Callable[[], UUID] = uuid4,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._repository = repository
        self._id_factory = id_factory
        self._clock = clock

    async def create_code(self, command: CreateDiscountCode) -> DiscountCode:
        _validate_value(command.discount_type, command.value)

        code = _normalize_code(command.code)
        existing = await self._repository.get_by_code(code)
        if existing is not None:
            raise DuplicateDiscountCodeError

        now = self._clock()
        discount_code = DiscountCode(
            id=self._id_factory(),
            code=code,
            discount_type=command.discount_type,
            value=command.value,
            is_active=True,
            expires_at=command.expires_at,
            max_redemptions=command.max_redemptions,
            redemption_count=0,
            created_at=now,
            updated_at=now,
        )
        saved = await self._repository.add(discount_code)
        logger.bind(discount_code_id=str(saved.id), code=code).info("Discount code created")
        return saved

    async def get_by_id(self, discount_code_id: UUID) -> DiscountCode:
        discount_code = await self._repository.get_by_id(discount_code_id)
        if discount_code is None:
            raise DiscountCodeNotFoundError
        return discount_code

    async def update_code(
        self, discount_code_id: UUID, command: UpdateDiscountCode
    ) -> DiscountCode:
        _validate_value(command.discount_type, command.value)

        discount_code = await self.get_by_id(discount_code_id)
        updated = DiscountCode(
            id=discount_code.id,
            code=discount_code.code,
            discount_type=command.discount_type,
            value=command.value,
            is_active=discount_code.is_active,
            expires_at=command.expires_at,
            max_redemptions=command.max_redemptions,
            redemption_count=discount_code.redemption_count,
            created_at=discount_code.created_at,
            updated_at=self._clock(),
        )
        return await self._repository.update(updated)

    async def set_active(self, discount_code_id: UUID, is_active: bool) -> DiscountCode:
        discount_code = await self.get_by_id(discount_code_id)
        updated = DiscountCode(
            id=discount_code.id,
            code=discount_code.code,
            discount_type=discount_code.discount_type,
            value=discount_code.value,
            is_active=is_active,
            expires_at=discount_code.expires_at,
            max_redemptions=discount_code.max_redemptions,
            redemption_count=discount_code.redemption_count,
            created_at=discount_code.created_at,
            updated_at=self._clock(),
        )
        return await self._repository.update(updated)

    async def delete_code(self, discount_code_id: UUID) -> None:
        await self.get_by_id(discount_code_id)
        await self._repository.delete(discount_code_id)

    async def list_all(self) -> list[DiscountCode]:
        return await self._repository.list_all()
