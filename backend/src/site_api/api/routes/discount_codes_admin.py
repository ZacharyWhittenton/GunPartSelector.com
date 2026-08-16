from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from site_api.api.dependencies import get_discount_code_service, require_admin
from site_api.domain.discount_codes import (
    DiscountCode,
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

router = APIRouter(
    prefix="/admin/discount-codes",
    tags=["admin discount codes"],
    dependencies=[Depends(require_admin)],
)


class DiscountCodeResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

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


class CreateDiscountCodeRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    code: str = Field(min_length=1, max_length=40)
    discount_type: DiscountType
    value: int = Field(gt=0)
    expires_at: datetime | None = None
    max_redemptions: int | None = Field(default=None, gt=0)


class UpdateDiscountCodeRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    discount_type: DiscountType
    value: int = Field(gt=0)
    expires_at: datetime | None = None
    max_redemptions: int | None = Field(default=None, gt=0)


def to_response(discount_code: DiscountCode) -> DiscountCodeResponse:
    return DiscountCodeResponse(
        id=discount_code.id,
        code=discount_code.code,
        discount_type=discount_code.discount_type,
        value=discount_code.value,
        is_active=discount_code.is_active,
        expires_at=discount_code.expires_at,
        max_redemptions=discount_code.max_redemptions,
        redemption_count=discount_code.redemption_count,
        created_at=discount_code.created_at,
        updated_at=discount_code.updated_at,
    )


@router.get("", response_model=list[DiscountCodeResponse], response_model_by_alias=True)
async def list_discount_codes(
    service: Annotated[DiscountCodeService, Depends(get_discount_code_service)],
) -> list[DiscountCodeResponse]:
    codes = await service.list_all()
    return [to_response(code) for code in codes]


@router.post(
    "",
    response_model=DiscountCodeResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
)
async def create_discount_code(
    payload: CreateDiscountCodeRequest,
    service: Annotated[DiscountCodeService, Depends(get_discount_code_service)],
) -> DiscountCodeResponse:
    try:
        code = await service.create_code(
            CreateDiscountCode(
                code=payload.code,
                discount_type=payload.discount_type,
                value=payload.value,
                expires_at=payload.expires_at,
                max_redemptions=payload.max_redemptions,
            )
        )
    except DuplicateDiscountCodeError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A discount code with that code already exists",
        ) from error
    except DiscountCodeInvalidError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid discount value for this discount type",
        ) from error

    return to_response(code)


@router.patch(
    "/{discount_code_id}",
    response_model=DiscountCodeResponse,
    response_model_by_alias=True,
)
async def update_discount_code(
    discount_code_id: UUID,
    payload: UpdateDiscountCodeRequest,
    service: Annotated[DiscountCodeService, Depends(get_discount_code_service)],
) -> DiscountCodeResponse:
    try:
        code = await service.update_code(
            discount_code_id,
            UpdateDiscountCode(
                discount_type=payload.discount_type,
                value=payload.value,
                expires_at=payload.expires_at,
                max_redemptions=payload.max_redemptions,
            ),
        )
    except DiscountCodeNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Discount code not found",
        ) from error
    except DiscountCodeInvalidError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid discount value for this discount type",
        ) from error

    return to_response(code)


@router.post(
    "/{discount_code_id}/deactivate",
    response_model=DiscountCodeResponse,
    response_model_by_alias=True,
)
async def deactivate_discount_code(
    discount_code_id: UUID,
    service: Annotated[DiscountCodeService, Depends(get_discount_code_service)],
) -> DiscountCodeResponse:
    try:
        code = await service.set_active(discount_code_id, False)
    except DiscountCodeNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Discount code not found",
        ) from error

    return to_response(code)


@router.post(
    "/{discount_code_id}/activate",
    response_model=DiscountCodeResponse,
    response_model_by_alias=True,
)
async def activate_discount_code(
    discount_code_id: UUID,
    service: Annotated[DiscountCodeService, Depends(get_discount_code_service)],
) -> DiscountCodeResponse:
    try:
        code = await service.set_active(discount_code_id, True)
    except DiscountCodeNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Discount code not found",
        ) from error

    return to_response(code)


@router.delete("/{discount_code_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_discount_code(
    discount_code_id: UUID,
    service: Annotated[DiscountCodeService, Depends(get_discount_code_service)],
) -> None:
    try:
        await service.delete_code(discount_code_id)
    except DiscountCodeNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Discount code not found",
        ) from error
