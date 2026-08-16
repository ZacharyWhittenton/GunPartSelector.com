from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from site_api.api.dependencies import (
    get_marketplace_file_storage,
    get_marketplace_service,
    require_admin,
)
from site_api.api.routes.marketplace import OrderSummary, to_order_summary
from site_api.core.storage import LocalFileStorage
from site_api.domain.marketplace import (
    ItemHasOrdersError,
    ItemNotFoundError,
    MarketplaceItem,
    OrderStatus,
)
from site_api.domain.storage import FileTooLargeError, UnsupportedFileTypeError
from site_api.domain.users import AuthenticatedUser
from site_api.services.marketplace import CreateItem, MarketplaceService, UpdateItem

router = APIRouter(
    prefix="/admin/marketplace", tags=["admin marketplace"], dependencies=[Depends(require_admin)]
)


class AdminItemSummary(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: UUID
    name: str
    slug: str
    description: str
    price_cents: int
    image_url: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ItemWriteRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    price_cents: int = Field(ge=0)
    image_url: str | None = None


class ImageUploadResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    url: str


def _to_admin_summary(item: MarketplaceItem) -> AdminItemSummary:
    return AdminItemSummary(
        id=item.id,
        name=item.name,
        slug=item.slug,
        description=item.description,
        price_cents=item.price_cents,
        image_url=item.image_url,
        is_active=item.is_active,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.get("/items", response_model=list[AdminItemSummary], response_model_by_alias=True)
async def list_all_items(
    service: Annotated[MarketplaceService, Depends(get_marketplace_service)],
) -> list[AdminItemSummary]:
    items = await service.list_all_items()
    return [_to_admin_summary(item) for item in items]


@router.post(
    "/items",
    response_model=AdminItemSummary,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
)
async def create_item(
    payload: ItemWriteRequest,
    service: Annotated[MarketplaceService, Depends(get_marketplace_service)],
    current_user: Annotated[AuthenticatedUser, Depends(require_admin)],
) -> AdminItemSummary:
    item = await service.create_item(
        CreateItem(
            name=payload.name,
            description=payload.description,
            price_cents=payload.price_cents,
            image_url=payload.image_url,
            created_by_admin_id=current_user.id,
        )
    )
    return _to_admin_summary(item)


@router.patch(
    "/items/{item_id}",
    response_model=AdminItemSummary,
    response_model_by_alias=True,
)
async def update_item(
    item_id: UUID,
    payload: ItemWriteRequest,
    service: Annotated[MarketplaceService, Depends(get_marketplace_service)],
) -> AdminItemSummary:
    try:
        item = await service.update_item(
            item_id,
            UpdateItem(
                name=payload.name,
                description=payload.description,
                price_cents=payload.price_cents,
                image_url=payload.image_url,
            ),
        )
    except ItemNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        ) from error

    return _to_admin_summary(item)


@router.post(
    "/items/{item_id}/deactivate",
    response_model=AdminItemSummary,
    response_model_by_alias=True,
)
async def deactivate_item(
    item_id: UUID,
    service: Annotated[MarketplaceService, Depends(get_marketplace_service)],
) -> AdminItemSummary:
    try:
        item = await service.set_item_active(item_id, False)
    except ItemNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        ) from error

    return _to_admin_summary(item)


@router.post(
    "/items/{item_id}/activate",
    response_model=AdminItemSummary,
    response_model_by_alias=True,
)
async def activate_item(
    item_id: UUID,
    service: Annotated[MarketplaceService, Depends(get_marketplace_service)],
) -> AdminItemSummary:
    try:
        item = await service.set_item_active(item_id, True)
    except ItemNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        ) from error

    return _to_admin_summary(item)


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: UUID,
    service: Annotated[MarketplaceService, Depends(get_marketplace_service)],
) -> None:
    try:
        await service.delete_item(item_id)
    except ItemNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        ) from error
    except ItemHasOrdersError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This item has order history and can't be deleted. Deactivate it instead.",
        ) from error


@router.post(
    "/items/images",
    response_model=ImageUploadResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
)
async def upload_item_image(
    file: Annotated[UploadFile, File()],
    storage: Annotated[LocalFileStorage, Depends(get_marketplace_file_storage)],
) -> ImageUploadResponse:
    content = await file.read()

    try:
        url = await storage.save_image(content, file.content_type or "")
    except UnsupportedFileTypeError as error:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only JPEG, PNG, WebP, and GIF images are supported",
        ) from error
    except FileTooLargeError as error:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Image must be 5MB or smaller",
        ) from error

    return ImageUploadResponse(url=url)


@router.get(
    "/orders",
    response_model=list[OrderSummary],
    response_model_by_alias=True,
)
async def list_all_orders(
    service: Annotated[MarketplaceService, Depends(get_marketplace_service)],
    status_filter: Annotated[OrderStatus | None, Query(alias="status")] = None,
) -> list[OrderSummary]:
    orders = await service.list_all_orders(status_filter)
    summaries = []
    for order in orders:
        items = await service.list_order_items(order.id)
        summaries.append(to_order_summary(order, items))
    return summaries
