from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

import stripe
from loguru import logger

from site_api.core.slugify import slugify
from site_api.domain.discount_codes import (
    DiscountCode,
    DiscountCodeInvalidError,
    DiscountCodeNotFoundError,
    DiscountCodeRepository,
    DiscountType,
)
from site_api.domain.marketplace import (
    EmptyCartError,
    InvalidWebhookSignatureError,
    ItemHasOrdersError,
    ItemNotFoundError,
    ItemNotPurchasableError,
    MarketplaceItem,
    MarketplaceItemRepository,
    MarketplaceNotConfiguredError,
    Order,
    OrderItem,
    OrderNotFoundError,
    OrderRepository,
    OrderStatus,
    WishlistItem,
    WishlistRepository,
)
from site_api.services.email import EmailService

MAX_LINE_QUANTITY = 20
MAX_PERCENT_VALUE = 100


@dataclass(frozen=True, slots=True)
class CreateItem:
    name: str
    description: str
    price_cents: int
    image_url: str | None
    created_by_admin_id: UUID


@dataclass(frozen=True, slots=True)
class UpdateItem:
    name: str
    description: str
    price_cents: int
    image_url: str | None


@dataclass(frozen=True, slots=True)
class CartLine:
    item_id: UUID
    quantity: int


@dataclass(frozen=True, slots=True)
class CreateCheckoutSession:
    lines: list[CartLine]
    customer_id: UUID | None
    customer_email: str | None
    discount_code: str | None = None


class MarketplaceService:
    def __init__(
        self,
        item_repository: MarketplaceItemRepository,
        order_repository: OrderRepository,
        wishlist_repository: WishlistRepository,
        stripe_client: stripe.StripeClient | None,
        webhook_secret: str | None,
        currency: str,
        success_url_template: str,
        cancel_url: str,
        email_service: EmailService | None = None,
        discount_code_repository: DiscountCodeRepository | None = None,
        id_factory: Callable[[], UUID] = uuid4,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._items = item_repository
        self._orders = order_repository
        self._wishlist = wishlist_repository
        self._stripe = stripe_client
        self._webhook_secret = webhook_secret
        self._currency = currency
        self._success_url_template = success_url_template
        self._cancel_url = cancel_url
        self._email = email_service or EmailService(None, None, None)
        self._discount_codes = discount_code_repository
        self._id_factory = id_factory
        self._clock = clock

    # --- Catalog ---------------------------------------------------------

    async def create_item(self, command: CreateItem) -> MarketplaceItem:
        slug = await self._unique_slug(command.name)
        now = self._clock()
        item = MarketplaceItem(
            id=self._id_factory(),
            name=command.name,
            slug=slug,
            description=command.description,
            price_cents=command.price_cents,
            image_url=command.image_url,
            is_active=True,
            created_by_admin_id=command.created_by_admin_id,
            created_at=now,
            updated_at=now,
        )
        saved = await self._items.add(item)
        logger.bind(item_id=str(saved.id)).info("Marketplace item created")
        return saved

    async def update_item(self, item_id: UUID, command: UpdateItem) -> MarketplaceItem:
        item = await self._items.get_by_id(item_id)
        if item is None:
            raise ItemNotFoundError

        updated = MarketplaceItem(
            id=item.id,
            name=command.name,
            slug=item.slug,
            description=command.description,
            price_cents=command.price_cents,
            image_url=command.image_url,
            is_active=item.is_active,
            created_by_admin_id=item.created_by_admin_id,
            created_at=item.created_at,
            updated_at=self._clock(),
        )
        return await self._items.update(updated)

    async def set_item_active(self, item_id: UUID, is_active: bool) -> MarketplaceItem:
        item = await self._items.get_by_id(item_id)
        if item is None:
            raise ItemNotFoundError

        updated = MarketplaceItem(
            id=item.id,
            name=item.name,
            slug=item.slug,
            description=item.description,
            price_cents=item.price_cents,
            image_url=item.image_url,
            is_active=is_active,
            created_by_admin_id=item.created_by_admin_id,
            created_at=item.created_at,
            updated_at=self._clock(),
        )
        return await self._items.update(updated)

    async def delete_item(self, item_id: UUID) -> None:
        item = await self._items.get_by_id(item_id)
        if item is None:
            raise ItemNotFoundError

        order_count = await self._orders.count_orders_for_item(item_id)
        if order_count > 0:
            raise ItemHasOrdersError

        await self._items.delete(item_id)

    async def list_active_items(self) -> list[MarketplaceItem]:
        return await self._items.list_active()

    async def list_all_items(self) -> list[MarketplaceItem]:
        return await self._items.list_all()

    async def get_item_by_slug(self, slug: str) -> MarketplaceItem:
        item = await self._items.get_by_slug(slug)
        if item is None:
            raise ItemNotFoundError
        return item

    # --- Checkout ----------------------------------------------------------

    async def create_checkout_session(self, command: CreateCheckoutSession) -> tuple[Order, str]:
        if self._stripe is None:
            raise MarketplaceNotConfiguredError

        if not command.lines:
            raise EmptyCartError

        merged_quantities: dict[UUID, int] = {}
        for line in command.lines:
            quantity = min(max(line.quantity, 1), MAX_LINE_QUANTITY)
            merged_quantities[line.item_id] = merged_quantities.get(line.item_id, 0) + quantity

        stripe_line_items = []
        order_items: list[OrderItem] = []
        total_cents = 0
        now = self._clock()
        order_id = self._id_factory()

        for item_id, quantity in merged_quantities.items():
            item = await self._items.get_by_id(item_id)
            if item is None:
                raise ItemNotFoundError
            if not item.is_active:
                raise ItemNotPurchasableError

            line_total = item.price_cents * quantity
            total_cents += line_total

            stripe_line_items.append(
                {
                    "price_data": {
                        "currency": self._currency,
                        "unit_amount": item.price_cents,
                        "product_data": {"name": item.name},
                    },
                    "quantity": quantity,
                }
            )
            order_items.append(
                OrderItem(
                    id=self._id_factory(),
                    order_id=order_id,
                    marketplace_item_id=item.id,
                    item_name=item.name,
                    unit_price_cents=item.price_cents,
                    quantity=quantity,
                    line_total_cents=line_total,
                )
            )

        applied_code = None
        discount_cents = 0
        session_params: dict[str, object] = {
            "mode": "payment",
            "line_items": stripe_line_items,
            "success_url": self._success_url_template,
            "cancel_url": self._cancel_url,
            **({"customer_email": command.customer_email} if command.customer_email else {}),
        }

        if command.discount_code:
            applied_code, discount_cents = await self._apply_discount_code(
                command.discount_code, total_cents
            )
            if discount_cents > 0:
                coupon_params: dict[str, object] = {"duration": "once"}
                if applied_code.discount_type is DiscountType.PERCENT:
                    coupon_params["percent_off"] = float(applied_code.value)
                else:
                    coupon_params["amount_off"] = discount_cents
                    coupon_params["currency"] = self._currency
                coupon = await self._stripe.v1.coupons.create_async(coupon_params)
                session_params["discounts"] = [{"coupon": coupon.id}]

        session = await self._stripe.v1.checkout.sessions.create_async(session_params)

        order = Order(
            id=order_id,
            stripe_checkout_session_id=session.id,
            stripe_payment_intent_id=None,
            customer_id=command.customer_id,
            customer_email=command.customer_email,
            status=OrderStatus.OPEN,
            total_cents=total_cents - discount_cents,
            discount_code=applied_code.code if applied_code else None,
            discount_cents=discount_cents,
            created_at=now,
            updated_at=now,
        )
        saved = await self._orders.add(order, order_items)
        logger.bind(order_id=str(saved.id)).info("Checkout session created")
        return saved, session.url

    # --- Webhook -------------------------------------------------------------

    async def handle_webhook_event(self, payload: bytes, signature_header: str) -> None:
        if self._stripe is None or self._webhook_secret is None:
            raise MarketplaceNotConfiguredError

        try:
            event = stripe.Webhook.construct_event(payload, signature_header, self._webhook_secret)
        except (ValueError, stripe.SignatureVerificationError) as error:
            raise InvalidWebhookSignatureError from error

        event_type = event["type"]
        session_obj = event["data"]["object"].to_dict()

        if event_type == "checkout.session.completed":
            paid_order = await self._apply_status(
                session_obj["id"],
                OrderStatus.PAID,
                payment_intent_id=session_obj.get("payment_intent"),
                customer_email=(session_obj.get("customer_details") or {}).get("email"),
            )
            if paid_order is not None:
                items = await self._orders.list_items_for_order(paid_order.id)
                await self._email.send_order_confirmation(paid_order, items)
                await self._email.notify_admin_new_order(paid_order, items)
                if paid_order.discount_code is not None:
                    await self._record_discount_redemption(paid_order.discount_code)
        elif event_type == "checkout.session.expired":
            await self._apply_status(session_obj["id"], OrderStatus.EXPIRED)
        elif event_type == "checkout.session.async_payment_failed":
            await self._apply_status(session_obj["id"], OrderStatus.CANCELLED)
        else:
            logger.bind(event_type=event_type).info("Ignoring unhandled Stripe webhook event")

    async def _apply_status(
        self,
        stripe_checkout_session_id: str,
        status: OrderStatus,
        payment_intent_id: str | None = None,
        customer_email: str | None = None,
    ) -> Order | None:
        order = await self._orders.get_by_session_id(stripe_checkout_session_id)
        if order is None:
            logger.bind(session_id=stripe_checkout_session_id).warning(
                "Webhook referenced an unknown checkout session"
            )
            return None

        if order.status is not OrderStatus.OPEN:
            return None

        updated = await self._orders.update_status(
            order.id, status, payment_intent_id, customer_email
        )
        logger.bind(order_id=str(order.id), status=status.value).info("Order status updated")
        return updated

    async def _apply_discount_code(
        self, code: str, subtotal_cents: int
    ) -> tuple[DiscountCode, int]:
        if self._discount_codes is None:
            raise DiscountCodeNotFoundError

        discount_code = await self._discount_codes.get_by_code(code.strip().upper())
        if discount_code is None:
            raise DiscountCodeNotFoundError

        if not discount_code.is_active:
            raise DiscountCodeInvalidError
        if discount_code.expires_at is not None and discount_code.expires_at <= self._clock():
            raise DiscountCodeInvalidError
        if (
            discount_code.max_redemptions is not None
            and discount_code.redemption_count >= discount_code.max_redemptions
        ):
            raise DiscountCodeInvalidError

        if discount_code.discount_type is DiscountType.PERCENT:
            discount_cents = round(subtotal_cents * discount_code.value / 100)
        else:
            discount_cents = min(discount_code.value, subtotal_cents)

        return discount_code, discount_cents

    async def _record_discount_redemption(self, code: str) -> None:
        if self._discount_codes is None:
            return

        discount_code = await self._discount_codes.get_by_code(code)
        if discount_code is None:
            return

        await self._discount_codes.update(
            replace(
                discount_code,
                redemption_count=discount_code.redemption_count + 1,
                updated_at=self._clock(),
            )
        )
        logger.bind(code=code).info("Discount code redemption recorded")

    # --- Orders --------------------------------------------------------------

    async def list_my_orders(self, customer_id: UUID) -> list[Order]:
        return await self._orders.list_for_customer(customer_id)

    async def get_order_by_session_id(self, stripe_checkout_session_id: str) -> Order:
        order = await self._orders.get_by_session_id(stripe_checkout_session_id)
        if order is None:
            raise OrderNotFoundError
        return order

    async def list_order_items(self, order_id: UUID) -> list[OrderItem]:
        return await self._orders.list_items_for_order(order_id)

    async def list_all_orders(self, status: OrderStatus | None = None) -> list[Order]:
        return await self._orders.list_all(status)

    # --- Wishlist --------------------------------------------------------------

    async def add_to_wishlist(self, user_id: UUID, item_id: UUID) -> WishlistItem:
        existing = await self._wishlist.get(user_id, item_id)
        if existing is not None:
            return existing

        item = await self._items.get_by_id(item_id)
        if item is None:
            raise ItemNotFoundError

        wishlist_item = WishlistItem(
            id=self._id_factory(),
            user_id=user_id,
            marketplace_item_id=item_id,
            created_at=self._clock(),
        )
        return await self._wishlist.add(wishlist_item)

    async def remove_from_wishlist(self, user_id: UUID, item_id: UUID) -> None:
        await self._wishlist.remove(user_id, item_id)

    async def list_wishlist(self, user_id: UUID) -> list[WishlistItem]:
        return await self._wishlist.list_for_user(user_id)

    # --- Internal --------------------------------------------------------------

    async def _unique_slug(self, name: str) -> str:
        base_slug = slugify(name)
        slug = base_slug
        suffix = 2
        while await self._items.slug_exists(slug):
            slug = f"{base_slug}-{suffix}"
            suffix += 1
        return slug
