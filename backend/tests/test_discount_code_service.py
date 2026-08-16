from datetime import UTC, datetime
from itertools import count
from uuid import UUID

import pytest

from site_api.domain.discount_codes import (
    DiscountCodeInvalidError,
    DiscountCodeNotFoundError,
    DiscountType,
    DuplicateDiscountCodeError,
)
from site_api.services.discount_codes import (
    CreateDiscountCode,
    DiscountCodeService,
    UpdateDiscountCode,
)
from tests.conftest import InMemoryDiscountCodeRepository

NOW = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)


@pytest.fixture
def service(
    discount_code_repository: InMemoryDiscountCodeRepository,
) -> DiscountCodeService:
    ids = iter(UUID(int=n) for n in count(1))
    return DiscountCodeService(
        discount_code_repository,
        id_factory=lambda: next(ids),
        clock=lambda: NOW,
    )


def _create_command(**overrides: object) -> CreateDiscountCode:
    defaults: dict[str, object] = {
        "code": "save10",
        "discount_type": DiscountType.PERCENT,
        "value": 10,
        "expires_at": None,
        "max_redemptions": None,
    }
    defaults.update(overrides)
    return CreateDiscountCode(**defaults)


@pytest.mark.asyncio
async def test_create_code_normalizes_to_uppercase(service: DiscountCodeService) -> None:
    code = await service.create_code(_create_command(code="  save10  "))

    assert code.code == "SAVE10"
    assert code.is_active is True
    assert code.redemption_count == 0


@pytest.mark.asyncio
async def test_create_code_rejects_duplicate_case_insensitive(
    service: DiscountCodeService,
) -> None:
    await service.create_code(_create_command(code="SAVE10"))

    with pytest.raises(DuplicateDiscountCodeError):
        await service.create_code(_create_command(code="save10"))


@pytest.mark.asyncio
async def test_create_code_rejects_zero_or_negative_value(service: DiscountCodeService) -> None:
    with pytest.raises(DiscountCodeInvalidError):
        await service.create_code(_create_command(value=0))


@pytest.mark.asyncio
async def test_create_code_rejects_percent_over_100(service: DiscountCodeService) -> None:
    with pytest.raises(DiscountCodeInvalidError):
        await service.create_code(_create_command(discount_type=DiscountType.PERCENT, value=101))


@pytest.mark.asyncio
async def test_fixed_discount_allows_value_over_100(service: DiscountCodeService) -> None:
    code = await service.create_code(_create_command(discount_type=DiscountType.FIXED, value=5000))

    assert code.value == 5000


@pytest.mark.asyncio
async def test_update_code_changes_value_and_expiry(service: DiscountCodeService) -> None:
    code = await service.create_code(_create_command())
    new_expiry = datetime(2026, 12, 31, tzinfo=UTC)

    updated = await service.update_code(
        code.id,
        UpdateDiscountCode(
            discount_type=DiscountType.FIXED,
            value=500,
            expires_at=new_expiry,
            max_redemptions=10,
        ),
    )

    assert updated.discount_type is DiscountType.FIXED
    assert updated.value == 500
    assert updated.expires_at == new_expiry
    assert updated.max_redemptions == 10
    assert updated.code == "SAVE10"


@pytest.mark.asyncio
async def test_update_code_raises_when_missing(service: DiscountCodeService) -> None:
    with pytest.raises(DiscountCodeNotFoundError):
        await service.update_code(
            UUID(int=999),
            UpdateDiscountCode(
                discount_type=DiscountType.PERCENT,
                value=10,
                expires_at=None,
                max_redemptions=None,
            ),
        )


@pytest.mark.asyncio
async def test_set_active_toggles_flag(service: DiscountCodeService) -> None:
    code = await service.create_code(_create_command())

    deactivated = await service.set_active(code.id, False)
    assert deactivated.is_active is False

    reactivated = await service.set_active(code.id, True)
    assert reactivated.is_active is True


@pytest.mark.asyncio
async def test_delete_code_removes_it(service: DiscountCodeService) -> None:
    code = await service.create_code(_create_command())

    await service.delete_code(code.id)

    assert await service.list_all() == []


@pytest.mark.asyncio
async def test_delete_code_raises_when_missing(service: DiscountCodeService) -> None:
    with pytest.raises(DiscountCodeNotFoundError):
        await service.delete_code(UUID(int=999))


@pytest.mark.asyncio
async def test_list_all_returns_every_code(service: DiscountCodeService) -> None:
    await service.create_code(_create_command(code="ONE"))
    await service.create_code(_create_command(code="TWO"))

    codes = await service.list_all()

    assert {code.code for code in codes} == {"ONE", "TWO"}
