from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID


class OrderStatus(StrEnum):
    OPEN = "open"
    PAID = "paid"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class VariantStockStatus(StrEnum):
    IN_STOCK = "in_stock"
    OUT_OF_STOCK = "out_of_stock"


@dataclass(frozen=True, slots=True)
class MarketplaceItem:
    id: UUID
    name: str
    slug: str
    description: str
    price_cents: int
    image_url: str | None
    is_active: bool
    created_by_admin_id: UUID
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ItemVariant:
    id: UUID
    marketplace_item_id: UUID
    label: str
    sort_order: int
    stock_status: VariantStockStatus
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class VariantInput:
    """Desired state of one variant, as submitted by an admin write."""

    label: str
    sort_order: int
    stock_status: VariantStockStatus


@dataclass(frozen=True, slots=True)
class OrderItem:
    id: UUID
    order_id: UUID
    marketplace_item_id: UUID | None
    variant_id: UUID | None
    variant_label: str
    item_name: str
    unit_price_cents: int
    quantity: int
    line_total_cents: int


@dataclass(frozen=True, slots=True)
class Order:
    id: UUID
    stripe_checkout_session_id: str
    stripe_payment_intent_id: str | None
    customer_id: UUID | None
    customer_email: str | None
    status: OrderStatus
    total_cents: int
    discount_code: str | None
    discount_cents: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class WishlistItem:
    id: UUID
    user_id: UUID
    marketplace_item_id: UUID
    created_at: datetime


class ItemNotFoundError(Exception):
    """Raised when a referenced marketplace item does not exist."""


class ItemNotPurchasableError(Exception):
    """Raised when a cart references an inactive marketplace item at checkout time."""


class ItemHasOrdersError(Exception):
    """Raised when an admin tries to hard-delete an item that has order history."""


class VariantNotFoundError(Exception):
    """Raised when a referenced item variant does not exist or belongs to a different item."""


class VariantOutOfStockError(Exception):
    """Raised when a cart line references a variant that is currently out of stock."""


class EmptyVariantsError(Exception):
    """Raised when an admin submits an item with no variants."""


class DuplicateVariantLabelError(Exception):
    """Raised when an admin submits two variants with the same label for one item."""


class EmptyCartError(Exception):
    """Raised when checkout is attempted with no line items."""


class OrderNotFoundError(Exception):
    """Raised when a referenced order does not exist."""


class InvalidWebhookSignatureError(Exception):
    """Raised when a Stripe webhook payload fails signature verification."""


class MarketplaceNotConfiguredError(Exception):
    """Raised when checkout or the webhook is used before Stripe is configured."""


class MarketplaceItemRepository(Protocol):
    async def add(self, item: MarketplaceItem) -> MarketplaceItem: ...

    async def update(self, item: MarketplaceItem) -> MarketplaceItem: ...

    async def delete(self, item_id: UUID) -> None: ...

    async def get_by_id(self, item_id: UUID) -> MarketplaceItem | None: ...

    async def get_by_slug(self, slug: str) -> MarketplaceItem | None: ...

    async def slug_exists(self, slug: str) -> bool: ...

    async def list_active(self) -> list[MarketplaceItem]: ...

    async def list_all(self) -> list[MarketplaceItem]: ...

    async def list_variants_for_item(self, item_id: UUID) -> list[ItemVariant]: ...

    async def get_variant_by_id(self, variant_id: UUID) -> ItemVariant | None: ...

    async def add_variant(self, variant: ItemVariant) -> ItemVariant: ...

    async def update_variant(self, variant: ItemVariant) -> ItemVariant: ...

    async def delete_variant(self, variant_id: UUID) -> None: ...


class OrderRepository(Protocol):
    async def add(self, order: Order, items: list[OrderItem]) -> Order: ...

    async def update_status(
        self,
        order_id: UUID,
        status: OrderStatus,
        stripe_payment_intent_id: str | None,
        customer_email: str | None,
    ) -> Order: ...

    async def get_by_id(self, order_id: UUID) -> Order | None: ...

    async def get_by_session_id(self, stripe_checkout_session_id: str) -> Order | None: ...

    async def list_items_for_order(self, order_id: UUID) -> list[OrderItem]: ...

    async def list_for_customer(self, customer_id: UUID) -> list[Order]: ...

    async def list_all(self, status: OrderStatus | None = None) -> list[Order]: ...

    async def count_orders_for_item(self, item_id: UUID) -> int: ...


class WishlistRepository(Protocol):
    async def add(self, wishlist_item: WishlistItem) -> WishlistItem: ...

    async def remove(self, user_id: UUID, marketplace_item_id: UUID) -> None: ...

    async def get(self, user_id: UUID, marketplace_item_id: UUID) -> WishlistItem | None: ...

    async def list_for_user(self, user_id: UUID) -> list[WishlistItem]: ...
