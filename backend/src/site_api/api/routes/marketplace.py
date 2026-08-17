from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from site_api.api.dependencies import (
    get_current_user,
    get_marketplace_service,
    get_optional_current_user,
)
from site_api.domain.discount_codes import DiscountCodeInvalidError, DiscountCodeNotFoundError
from site_api.domain.marketplace import (
    EmptyCartError,
    InvalidWebhookSignatureError,
    ItemNotFoundError,
    ItemNotPurchasableError,
    ItemVariant,
    MarketplaceItem,
    MarketplaceNotConfiguredError,
    Order,
    OrderItem,
    OrderNotFoundError,
    VariantNotFoundError,
    VariantOutOfStockError,
)
from site_api.domain.users import AuthenticatedUser
from site_api.services.marketplace import CartLine, CreateCheckoutSession, MarketplaceService

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


class VariantSummary(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: UUID
    label: str
    sort_order: int
    stock_status: str


class ItemSummary(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: UUID
    name: str
    slug: str
    description: str
    price_cents: int
    image_url: str | None
    variants: list[VariantSummary]


class CheckoutLineRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    item_id: UUID
    variant_id: UUID
    quantity: int = Field(ge=1, le=20)


class CheckoutRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    items: list[CheckoutLineRequest] = Field(min_length=1, max_length=50)
    discount_code: str | None = Field(default=None, max_length=40)


class CheckoutResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    checkout_url: str


class OrderItemSummary(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    item_name: str
    variant_label: str
    unit_price_cents: int
    quantity: int
    line_total_cents: int


class OrderSummary(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: UUID
    status: str
    total_cents: int
    discount_code: str | None
    discount_cents: int
    created_at: datetime
    items: list[OrderItemSummary]


class WishlistAddRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    item_id: UUID


class WishlistItemResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: UUID
    marketplace_item_id: UUID
    created_at: datetime


def to_variant_summary(variant: ItemVariant) -> VariantSummary:
    return VariantSummary(
        id=variant.id,
        label=variant.label,
        sort_order=variant.sort_order,
        stock_status=variant.stock_status.value,
    )


def to_item_summary(item: MarketplaceItem, variants: list[ItemVariant]) -> ItemSummary:
    return ItemSummary(
        id=item.id,
        name=item.name,
        slug=item.slug,
        description=item.description,
        price_cents=item.price_cents,
        image_url=item.image_url,
        variants=[to_variant_summary(variant) for variant in variants],
    )


def to_order_summary(order: Order, items: list[OrderItem]) -> OrderSummary:
    return OrderSummary(
        id=order.id,
        status=order.status.value,
        total_cents=order.total_cents,
        discount_code=order.discount_code,
        discount_cents=order.discount_cents,
        created_at=order.created_at,
        items=[
            OrderItemSummary(
                item_name=item.item_name,
                variant_label=item.variant_label,
                unit_price_cents=item.unit_price_cents,
                quantity=item.quantity,
                line_total_cents=item.line_total_cents,
            )
            for item in items
        ],
    )


@router.get("/items", response_model=list[ItemSummary], response_model_by_alias=True)
async def list_items(
    service: Annotated[MarketplaceService, Depends(get_marketplace_service)],
) -> list[ItemSummary]:
    items = await service.list_active_items()
    summaries = []
    for item in items:
        variants = await service.list_variants_for_item(item.id)
        summaries.append(to_item_summary(item, variants))
    return summaries


@router.get("/items/{slug}", response_model=ItemSummary, response_model_by_alias=True)
async def get_item(
    slug: str,
    service: Annotated[MarketplaceService, Depends(get_marketplace_service)],
) -> ItemSummary:
    try:
        item = await service.get_item_by_slug(slug)
    except ItemNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        ) from error

    variants = await service.list_variants_for_item(item.id)
    return to_item_summary(item, variants)


@router.post(
    "/checkout",
    response_model=CheckoutResponse,
    response_model_by_alias=True,
)
async def create_checkout_session(
    payload: CheckoutRequest,
    service: Annotated[MarketplaceService, Depends(get_marketplace_service)],
    current_user: Annotated[AuthenticatedUser | None, Depends(get_optional_current_user)],
) -> CheckoutResponse:
    try:
        _, checkout_url = await service.create_checkout_session(
            CreateCheckoutSession(
                lines=[
                    CartLine(
                        item_id=line.item_id,
                        variant_id=line.variant_id,
                        quantity=line.quantity,
                    )
                    for line in payload.items
                ],
                customer_id=current_user.id if current_user else None,
                customer_email=current_user.email_address if current_user else None,
                discount_code=payload.discount_code,
            )
        )
    except MarketplaceNotConfiguredError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The marketplace is not configured yet.",
        ) from error
    except EmptyCartError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your cart is empty",
        ) from error
    except ItemNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One of the items in your cart no longer exists",
        ) from error
    except ItemNotPurchasableError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="One of the items in your cart is no longer available",
        ) from error
    except VariantNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One of the selected sizes no longer exists",
        ) from error
    except VariantOutOfStockError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="One of the selected sizes is out of stock",
        ) from error
    except (DiscountCodeNotFoundError, DiscountCodeInvalidError) as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That discount code is invalid or expired.",
        ) from error

    return CheckoutResponse(checkout_url=checkout_url)


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    service: Annotated[MarketplaceService, Depends(get_marketplace_service)],
    stripe_signature: Annotated[str | None, Header(alias="Stripe-Signature")] = None,
) -> dict[str, bool]:
    if stripe_signature is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing signature")

    payload = await request.body()

    try:
        await service.handle_webhook_event(payload, stripe_signature)
    except MarketplaceNotConfiguredError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The marketplace is not configured yet.",
        ) from error
    except InvalidWebhookSignatureError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature",
        ) from error

    return {"received": True}


@router.get(
    "/orders/mine",
    response_model=list[OrderSummary],
    response_model_by_alias=True,
)
async def list_my_orders(
    service: Annotated[MarketplaceService, Depends(get_marketplace_service)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> list[OrderSummary]:
    orders = await service.list_my_orders(current_user.id)
    summaries = []
    for order in orders:
        items = await service.list_order_items(order.id)
        summaries.append(to_order_summary(order, items))
    return summaries


@router.get(
    "/orders/by-session/{session_id}",
    response_model=OrderSummary,
    response_model_by_alias=True,
)
async def get_order_by_session(
    session_id: str,
    service: Annotated[MarketplaceService, Depends(get_marketplace_service)],
) -> OrderSummary:
    try:
        order = await service.get_order_by_session_id(session_id)
    except OrderNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        ) from error

    items = await service.list_order_items(order.id)
    return to_order_summary(order, items)


@router.get(
    "/wishlist",
    response_model=list[WishlistItemResponse],
    response_model_by_alias=True,
)
async def list_wishlist(
    service: Annotated[MarketplaceService, Depends(get_marketplace_service)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> list[WishlistItemResponse]:
    wishlist = await service.list_wishlist(current_user.id)
    return [
        WishlistItemResponse(
            id=entry.id, marketplace_item_id=entry.marketplace_item_id, created_at=entry.created_at
        )
        for entry in wishlist
    ]


@router.post(
    "/wishlist",
    response_model=WishlistItemResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
)
async def add_to_wishlist(
    payload: WishlistAddRequest,
    service: Annotated[MarketplaceService, Depends(get_marketplace_service)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> WishlistItemResponse:
    try:
        entry = await service.add_to_wishlist(current_user.id, payload.item_id)
    except ItemNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        ) from error

    return WishlistItemResponse(
        id=entry.id, marketplace_item_id=entry.marketplace_item_id, created_at=entry.created_at
    )


@router.delete("/wishlist/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_wishlist(
    item_id: UUID,
    service: Annotated[MarketplaceService, Depends(get_marketplace_service)],
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> None:
    await service.remove_from_wishlist(current_user.id, item_id)
