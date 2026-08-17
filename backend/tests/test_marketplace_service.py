import hashlib
import hmac
import json
import time
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from itertools import count
from uuid import UUID

import pytest

from site_api.domain.discount_codes import (
    DiscountCodeInvalidError,
    DiscountCodeNotFoundError,
    DiscountType,
)
from site_api.domain.marketplace import (
    DuplicateVariantLabelError,
    EmptyCartError,
    EmptyVariantsError,
    InvalidWebhookSignatureError,
    ItemHasOrdersError,
    ItemNotFoundError,
    ItemNotPurchasableError,
    MarketplaceNotConfiguredError,
    OrderNotFoundError,
    OrderStatus,
    VariantInput,
    VariantNotFoundError,
    VariantOutOfStockError,
    VariantStockStatus,
)
from site_api.services.discount_codes import CreateDiscountCode, DiscountCodeService
from site_api.services.email import EmailService
from site_api.services.marketplace import (
    CartLine,
    CreateCheckoutSession,
    CreateItem,
    MarketplaceService,
    UpdateItem,
)
from tests.conftest import (
    FakeSesClient,
    FakeStripeClient,
    InMemoryDiscountCodeRepository,
    InMemoryMarketplaceItemRepository,
    InMemoryOrderRepository,
    InMemoryWishlistRepository,
)

ADMIN_ID = UUID("11111111-1111-1111-1111-111111111111")
CUSTOMER_ID = UUID("22222222-2222-2222-2222-222222222222")
OTHER_CUSTOMER_ID = UUID("33333333-3333-3333-3333-333333333333")
WEBHOOK_SECRET = "whsec_test_secret"

NOW = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)


@pytest.fixture
def service(
    marketplace_item_repository: InMemoryMarketplaceItemRepository,
    order_repository: InMemoryOrderRepository,
    wishlist_repository: InMemoryWishlistRepository,
    fake_stripe_client: FakeStripeClient,
    email_service: EmailService,
    discount_code_repository: InMemoryDiscountCodeRepository,
) -> MarketplaceService:
    ids = iter(UUID(int=n) for n in count(1))
    return MarketplaceService(
        marketplace_item_repository,
        order_repository,
        wishlist_repository,
        fake_stripe_client,  # type: ignore[arg-type]
        WEBHOOK_SECRET,
        "usd",
        "http://localhost:4200/marketplace/success?session_id={CHECKOUT_SESSION_ID}",
        "http://localhost:4200/cart",
        email_service,
        discount_code_repository,
        id_factory=lambda: next(ids),
        clock=lambda: NOW,
    )


@pytest.fixture
def discount_service(
    discount_code_repository: InMemoryDiscountCodeRepository,
) -> DiscountCodeService:
    return DiscountCodeService(discount_code_repository, clock=lambda: NOW)


def _default_variants() -> list[VariantInput]:
    return [VariantInput(label="One Size", sort_order=0, stock_status=VariantStockStatus.IN_STOCK)]


def _create_command(**overrides: object) -> CreateItem:
    defaults: dict[str, object] = {
        "name": "Website Audit",
        "description": "A full technical and SEO audit.",
        "price_cents": 5000,
        "image_url": None,
        "created_by_admin_id": ADMIN_ID,
        "variants": _default_variants(),
    }
    defaults.update(overrides)
    return CreateItem(**defaults)


def _sign(payload: bytes, secret: str = WEBHOOK_SECRET, timestamp: int | None = None) -> str:
    ts = timestamp if timestamp is not None else int(time.time())
    signed_payload = f"{ts}.{payload.decode()}"
    signature = hmac.new(secret.encode(), signed_payload.encode(), hashlib.sha256).hexdigest()
    return f"t={ts},v1={signature}"


def _event_payload(
    event_type: str,
    session_id: str,
    payment_intent: str | None = "pi_test_1",
    customer_email: str | None = "guest@example.com",
) -> bytes:
    body = {
        "id": "evt_test_1",
        "object": "event",
        "type": event_type,
        "data": {
            "object": {
                "id": session_id,
                "object": "checkout.session",
                "payment_intent": payment_intent,
                "customer_details": {"email": customer_email} if customer_email else None,
            }
        },
    }
    return json.dumps(body).encode()


@pytest.mark.asyncio
async def test_create_item_is_active_and_slugified(service: MarketplaceService) -> None:
    item = await service.create_item(_create_command())

    assert item.is_active is True
    assert item.slug == "website-audit"


@pytest.mark.asyncio
async def test_create_item_rejects_empty_variants(service: MarketplaceService) -> None:
    with pytest.raises(EmptyVariantsError):
        await service.create_item(_create_command(variants=[]))


@pytest.mark.asyncio
async def test_create_item_rejects_duplicate_variant_labels(
    service: MarketplaceService,
) -> None:
    with pytest.raises(DuplicateVariantLabelError):
        await service.create_item(
            _create_command(
                variants=[
                    VariantInput(label="M", sort_order=0, stock_status=VariantStockStatus.IN_STOCK),
                    VariantInput(label="m", sort_order=1, stock_status=VariantStockStatus.IN_STOCK),
                ]
            )
        )


@pytest.mark.asyncio
async def test_checkout_rejects_variant_from_a_different_item(
    service: MarketplaceService,
) -> None:
    item = await service.create_item(_create_command())
    other_item = await service.create_item(_create_command(name="Other Item"))
    other_variant_id = (await service.list_variants_for_item(other_item.id))[0].id

    with pytest.raises(VariantNotFoundError):
        await service.create_checkout_session(
            CreateCheckoutSession(
                lines=[CartLine(item_id=item.id, variant_id=other_variant_id, quantity=1)],
                customer_id=None,
                customer_email=None,
            )
        )


@pytest.mark.asyncio
async def test_checkout_rejects_out_of_stock_variant(service: MarketplaceService) -> None:
    item = await service.create_item(
        _create_command(
            variants=[
                VariantInput(
                    label="XXL", sort_order=0, stock_status=VariantStockStatus.OUT_OF_STOCK
                )
            ]
        )
    )
    variant_id = (await service.list_variants_for_item(item.id))[0].id

    with pytest.raises(VariantOutOfStockError):
        await service.create_checkout_session(
            CreateCheckoutSession(
                lines=[CartLine(item_id=item.id, variant_id=variant_id, quantity=1)],
                customer_id=None,
                customer_email=None,
            )
        )


@pytest.mark.asyncio
async def test_update_item_syncs_variants_add_and_remove(
    service: MarketplaceService,
) -> None:
    item = await service.create_item(
        _create_command(
            variants=[
                VariantInput(label="S", sort_order=0, stock_status=VariantStockStatus.IN_STOCK),
                VariantInput(label="M", sort_order=1, stock_status=VariantStockStatus.IN_STOCK),
            ]
        )
    )

    await service.update_item(
        item.id,
        UpdateItem(
            name=item.name,
            description=item.description,
            price_cents=item.price_cents,
            image_url=item.image_url,
            variants=[
                VariantInput(label="M", sort_order=0, stock_status=VariantStockStatus.IN_STOCK),
                VariantInput(label="L", sort_order=1, stock_status=VariantStockStatus.IN_STOCK),
            ],
        ),
    )

    labels = {variant.label for variant in await service.list_variants_for_item(item.id)}
    assert labels == {"M", "L"}


@pytest.mark.asyncio
async def test_update_item_raises_when_missing(service: MarketplaceService) -> None:
    with pytest.raises(ItemNotFoundError):
        await service.update_item(
            UUID(int=999),
            UpdateItem(
                name="X", description="Y", price_cents=100, image_url=None,
                variants=_default_variants(),
            ),
        )


@pytest.mark.asyncio
async def test_deactivated_item_excluded_from_active_listing(service: MarketplaceService) -> None:
    item = await service.create_item(_create_command())
    await service.set_item_active(item.id, False)

    active = await service.list_active_items()
    all_items = await service.list_all_items()

    assert active == []
    assert len(all_items) == 1


@pytest.mark.asyncio
async def test_delete_item_succeeds_when_no_orders(service: MarketplaceService) -> None:
    item = await service.create_item(_create_command())

    await service.delete_item(item.id)

    assert await service.list_all_items() == []


@pytest.mark.asyncio
async def test_delete_item_rejects_when_orders_exist(service: MarketplaceService) -> None:
    item = await service.create_item(_create_command())
    await service.create_checkout_session(
        CreateCheckoutSession(
            lines=[CartLine(item_id=item.id, variant_id=(await service.list_variants_for_item(item.id))[0].id, quantity=1)],
            customer_id=None,
            customer_email=None,
        )
    )

    with pytest.raises(ItemHasOrdersError):
        await service.delete_item(item.id)


@pytest.mark.asyncio
async def test_checkout_uses_current_item_price_not_stale_client_value(
    service: MarketplaceService,
) -> None:
    item = await service.create_item(_create_command(price_cents=5000))
    await service.update_item(
        item.id,
        UpdateItem(
            name=item.name, description=item.description, price_cents=9900, image_url=None,
            variants=_default_variants(),
        ),
    )

    order, _ = await service.create_checkout_session(
        CreateCheckoutSession(
            lines=[CartLine(item_id=item.id, variant_id=(await service.list_variants_for_item(item.id))[0].id, quantity=2)],
            customer_id=None,
            customer_email=None,
        )
    )

    assert order.total_cents == 9900 * 2


@pytest.mark.asyncio
async def test_checkout_clamps_quantity_to_max(service: MarketplaceService) -> None:
    item = await service.create_item(_create_command(price_cents=100))

    order, _ = await service.create_checkout_session(
        CreateCheckoutSession(
            lines=[CartLine(item_id=item.id, variant_id=(await service.list_variants_for_item(item.id))[0].id, quantity=999)],
            customer_id=None,
            customer_email=None,
        )
    )

    assert order.total_cents == 100 * 20


@pytest.mark.asyncio
async def test_checkout_clamps_quantity_to_min(service: MarketplaceService) -> None:
    item = await service.create_item(_create_command(price_cents=100))

    order, _ = await service.create_checkout_session(
        CreateCheckoutSession(
            lines=[CartLine(item_id=item.id, variant_id=(await service.list_variants_for_item(item.id))[0].id, quantity=0)],
            customer_id=None,
            customer_email=None,
        )
    )

    assert order.total_cents == 100


@pytest.mark.asyncio
async def test_checkout_rejects_empty_cart(service: MarketplaceService) -> None:
    with pytest.raises(EmptyCartError):
        await service.create_checkout_session(
            CreateCheckoutSession(lines=[], customer_id=None, customer_email=None)
        )


@pytest.mark.asyncio
async def test_checkout_rejects_unknown_item(service: MarketplaceService) -> None:
    with pytest.raises(ItemNotFoundError):
        await service.create_checkout_session(
            CreateCheckoutSession(
                lines=[CartLine(item_id=UUID(int=999), variant_id=UUID(int=1), quantity=1)],
                customer_id=None,
                customer_email=None,
            )
        )


@pytest.mark.asyncio
async def test_checkout_rejects_inactive_item(service: MarketplaceService) -> None:
    item = await service.create_item(_create_command())
    await service.set_item_active(item.id, False)

    with pytest.raises(ItemNotPurchasableError):
        await service.create_checkout_session(
            CreateCheckoutSession(
                lines=[CartLine(item_id=item.id, variant_id=(await service.list_variants_for_item(item.id))[0].id, quantity=1)],
                customer_id=None,
                customer_email=None,
            )
        )


@pytest.mark.asyncio
async def test_checkout_raises_when_stripe_not_configured(
    marketplace_item_repository: InMemoryMarketplaceItemRepository,
    order_repository: InMemoryOrderRepository,
    wishlist_repository: InMemoryWishlistRepository,
) -> None:
    unconfigured = MarketplaceService(
        marketplace_item_repository,
        order_repository,
        wishlist_repository,
        None,
        None,
        "usd",
        "http://localhost:4200/marketplace/success?session_id={CHECKOUT_SESSION_ID}",
        "http://localhost:4200/cart",
    )

    with pytest.raises(MarketplaceNotConfiguredError):
        await unconfigured.create_checkout_session(
            CreateCheckoutSession(
                lines=[CartLine(item_id=UUID(int=1), variant_id=UUID(int=1), quantity=1)],
                customer_id=None,
                customer_email=None,
            )
        )


@pytest.mark.asyncio
async def test_webhook_raises_when_not_configured(
    marketplace_item_repository: InMemoryMarketplaceItemRepository,
    order_repository: InMemoryOrderRepository,
    wishlist_repository: InMemoryWishlistRepository,
) -> None:
    unconfigured = MarketplaceService(
        marketplace_item_repository,
        order_repository,
        wishlist_repository,
        None,
        None,
        "usd",
        "http://localhost:4200/marketplace/success?session_id={CHECKOUT_SESSION_ID}",
        "http://localhost:4200/cart",
    )

    with pytest.raises(MarketplaceNotConfiguredError):
        await unconfigured.handle_webhook_event(b"{}", "t=1,v1=abc")


@pytest.mark.asyncio
async def test_webhook_rejects_invalid_signature(service: MarketplaceService) -> None:
    payload = _event_payload("checkout.session.completed", "cs_test_1")

    with pytest.raises(InvalidWebhookSignatureError):
        await service.handle_webhook_event(payload, "t=123,v1=deadbeef")


@pytest.mark.asyncio
async def test_webhook_completed_marks_order_paid(service: MarketplaceService) -> None:
    item = await service.create_item(_create_command())
    order, _ = await service.create_checkout_session(
        CreateCheckoutSession(
            lines=[CartLine(item_id=item.id, variant_id=(await service.list_variants_for_item(item.id))[0].id, quantity=1)],
            customer_id=None,
            customer_email=None,
        )
    )

    payload = _event_payload(
        "checkout.session.completed",
        order.stripe_checkout_session_id,
        payment_intent="pi_live_1",
        customer_email="guest@example.com",
    )
    await service.handle_webhook_event(payload, _sign(payload))

    updated = await service.get_order_by_session_id(order.stripe_checkout_session_id)
    assert updated.status is OrderStatus.PAID
    assert updated.stripe_payment_intent_id == "pi_live_1"
    assert updated.customer_email == "guest@example.com"


@pytest.mark.asyncio
async def test_webhook_completed_sends_confirmation_and_admin_emails(
    service: MarketplaceService,
    fake_ses_client: FakeSesClient,
) -> None:
    item = await service.create_item(_create_command())
    order, _ = await service.create_checkout_session(
        CreateCheckoutSession(
            lines=[CartLine(item_id=item.id, variant_id=(await service.list_variants_for_item(item.id))[0].id, quantity=1)],
            customer_id=None,
            customer_email=None,
        )
    )

    payload = _event_payload(
        "checkout.session.completed",
        order.stripe_checkout_session_id,
        customer_email="guest@example.com",
    )
    await service.handle_webhook_event(payload, _sign(payload))

    assert len(fake_ses_client.sent) == 2
    recipients = {call["Destination"]["ToAddresses"][0] for call in fake_ses_client.sent}
    assert recipients == {"guest@example.com", "admin@example.com"}


@pytest.mark.asyncio
async def test_webhook_expired_does_not_send_order_emails(
    service: MarketplaceService,
    fake_ses_client: FakeSesClient,
) -> None:
    item = await service.create_item(_create_command())
    order, _ = await service.create_checkout_session(
        CreateCheckoutSession(
            lines=[CartLine(item_id=item.id, variant_id=(await service.list_variants_for_item(item.id))[0].id, quantity=1)],
            customer_id=None,
            customer_email=None,
        )
    )

    payload = _event_payload("checkout.session.expired", order.stripe_checkout_session_id)
    await service.handle_webhook_event(payload, _sign(payload))

    assert fake_ses_client.sent == []


@pytest.mark.asyncio
async def test_webhook_expired_marks_order_expired(service: MarketplaceService) -> None:
    item = await service.create_item(_create_command())
    order, _ = await service.create_checkout_session(
        CreateCheckoutSession(
            lines=[CartLine(item_id=item.id, variant_id=(await service.list_variants_for_item(item.id))[0].id, quantity=1)],
            customer_id=None,
            customer_email=None,
        )
    )

    payload = _event_payload("checkout.session.expired", order.stripe_checkout_session_id)
    await service.handle_webhook_event(payload, _sign(payload))

    updated = await service.get_order_by_session_id(order.stripe_checkout_session_id)
    assert updated.status is OrderStatus.EXPIRED


@pytest.mark.asyncio
async def test_webhook_async_payment_failed_marks_order_cancelled(
    service: MarketplaceService,
) -> None:
    item = await service.create_item(_create_command())
    order, _ = await service.create_checkout_session(
        CreateCheckoutSession(
            lines=[CartLine(item_id=item.id, variant_id=(await service.list_variants_for_item(item.id))[0].id, quantity=1)],
            customer_id=None,
            customer_email=None,
        )
    )

    payload = _event_payload(
        "checkout.session.async_payment_failed", order.stripe_checkout_session_id
    )
    await service.handle_webhook_event(payload, _sign(payload))

    updated = await service.get_order_by_session_id(order.stripe_checkout_session_id)
    assert updated.status is OrderStatus.CANCELLED


@pytest.mark.asyncio
async def test_webhook_ignores_unhandled_event_type(service: MarketplaceService) -> None:
    payload = _event_payload("payment_intent.created", "cs_unrelated")

    await service.handle_webhook_event(payload, _sign(payload))


@pytest.mark.asyncio
async def test_webhook_unknown_session_is_a_noop(service: MarketplaceService) -> None:
    payload = _event_payload("checkout.session.completed", "cs_never_created")

    await service.handle_webhook_event(payload, _sign(payload))


@pytest.mark.asyncio
async def test_webhook_is_idempotent_on_duplicate_delivery(service: MarketplaceService) -> None:
    item = await service.create_item(_create_command())
    order, _ = await service.create_checkout_session(
        CreateCheckoutSession(
            lines=[CartLine(item_id=item.id, variant_id=(await service.list_variants_for_item(item.id))[0].id, quantity=1)],
            customer_id=None,
            customer_email=None,
        )
    )

    completed_payload = _event_payload(
        "checkout.session.completed", order.stripe_checkout_session_id
    )
    await service.handle_webhook_event(completed_payload, _sign(completed_payload))

    expired_payload = _event_payload("checkout.session.expired", order.stripe_checkout_session_id)
    await service.handle_webhook_event(expired_payload, _sign(expired_payload))

    updated = await service.get_order_by_session_id(order.stripe_checkout_session_id)
    assert updated.status is OrderStatus.PAID


@pytest.mark.asyncio
async def test_duplicate_completed_delivery_only_emails_once(
    service: MarketplaceService,
    fake_ses_client: FakeSesClient,
) -> None:
    item = await service.create_item(_create_command())
    order, _ = await service.create_checkout_session(
        CreateCheckoutSession(
            lines=[CartLine(item_id=item.id, variant_id=(await service.list_variants_for_item(item.id))[0].id, quantity=1)],
            customer_id=None,
            customer_email=None,
        )
    )

    payload = _event_payload("checkout.session.completed", order.stripe_checkout_session_id)
    await service.handle_webhook_event(payload, _sign(payload))
    await service.handle_webhook_event(payload, _sign(payload))

    assert len(fake_ses_client.sent) == 2


@pytest.mark.asyncio
async def test_get_order_by_session_id_raises_when_missing(service: MarketplaceService) -> None:
    with pytest.raises(OrderNotFoundError):
        await service.get_order_by_session_id("cs_does_not_exist")


@pytest.mark.asyncio
async def test_list_my_orders_returns_only_own(service: MarketplaceService) -> None:
    item = await service.create_item(_create_command())
    await service.create_checkout_session(
        CreateCheckoutSession(
            lines=[CartLine(item_id=item.id, variant_id=(await service.list_variants_for_item(item.id))[0].id, quantity=1)],
            customer_id=CUSTOMER_ID,
            customer_email="customer@example.com",
        )
    )
    await service.create_checkout_session(
        CreateCheckoutSession(
            lines=[CartLine(item_id=item.id, variant_id=(await service.list_variants_for_item(item.id))[0].id, quantity=1)],
            customer_id=OTHER_CUSTOMER_ID,
            customer_email="other@example.com",
        )
    )

    mine = await service.list_my_orders(CUSTOMER_ID)

    assert len(mine) == 1
    assert mine[0].customer_id == CUSTOMER_ID


@pytest.mark.asyncio
async def test_wishlist_add_is_idempotent(service: MarketplaceService) -> None:
    item = await service.create_item(_create_command())

    first = await service.add_to_wishlist(CUSTOMER_ID, item.id)
    second = await service.add_to_wishlist(CUSTOMER_ID, item.id)

    assert first.id == second.id
    assert len(await service.list_wishlist(CUSTOMER_ID)) == 1


@pytest.mark.asyncio
async def test_wishlist_add_raises_for_unknown_item(service: MarketplaceService) -> None:
    with pytest.raises(ItemNotFoundError):
        await service.add_to_wishlist(CUSTOMER_ID, UUID(int=999))


@pytest.mark.asyncio
async def test_wishlist_remove(service: MarketplaceService) -> None:
    item = await service.create_item(_create_command())
    await service.add_to_wishlist(CUSTOMER_ID, item.id)

    await service.remove_from_wishlist(CUSTOMER_ID, item.id)

    assert await service.list_wishlist(CUSTOMER_ID) == []


@pytest.mark.asyncio
async def test_checkout_applies_percent_discount(
    service: MarketplaceService,
    discount_service: DiscountCodeService,
    fake_stripe_client: FakeStripeClient,
) -> None:
    item = await service.create_item(_create_command(price_cents=10000))
    await discount_service.create_code(
        CreateDiscountCode(
            code="SAVE10",
            discount_type=DiscountType.PERCENT,
            value=10,
            expires_at=None,
            max_redemptions=None,
        )
    )

    order, _ = await service.create_checkout_session(
        CreateCheckoutSession(
            lines=[CartLine(item_id=item.id, variant_id=(await service.list_variants_for_item(item.id))[0].id, quantity=1)],
            customer_id=None,
            customer_email=None,
            discount_code="save10",
        )
    )

    assert order.discount_code == "SAVE10"
    assert order.discount_cents == 1000
    assert order.total_cents == 9000
    assert fake_stripe_client.v1.coupons.created_params[0]["percent_off"] == 10.0


@pytest.mark.asyncio
async def test_checkout_applies_fixed_discount_clamped_to_subtotal(
    service: MarketplaceService,
    discount_service: DiscountCodeService,
    fake_stripe_client: FakeStripeClient,
) -> None:
    item = await service.create_item(_create_command(price_cents=500))
    await discount_service.create_code(
        CreateDiscountCode(
            code="BIGDISCOUNT",
            discount_type=DiscountType.FIXED,
            value=5000,
            expires_at=None,
            max_redemptions=None,
        )
    )

    order, _ = await service.create_checkout_session(
        CreateCheckoutSession(
            lines=[CartLine(item_id=item.id, variant_id=(await service.list_variants_for_item(item.id))[0].id, quantity=1)],
            customer_id=None,
            customer_email=None,
            discount_code="BIGDISCOUNT",
        )
    )

    assert order.discount_cents == 500
    assert order.total_cents == 0
    assert fake_stripe_client.v1.coupons.created_params[0]["amount_off"] == 500


@pytest.mark.asyncio
async def test_checkout_rejects_unknown_discount_code(service: MarketplaceService) -> None:
    item = await service.create_item(_create_command())

    with pytest.raises(DiscountCodeNotFoundError):
        await service.create_checkout_session(
            CreateCheckoutSession(
                lines=[CartLine(item_id=item.id, variant_id=(await service.list_variants_for_item(item.id))[0].id, quantity=1)],
                customer_id=None,
                customer_email=None,
                discount_code="NOPE",
            )
        )


@pytest.mark.asyncio
async def test_checkout_rejects_inactive_discount_code(
    service: MarketplaceService,
    discount_service: DiscountCodeService,
) -> None:
    item = await service.create_item(_create_command())
    code = await discount_service.create_code(
        CreateDiscountCode(
            code="OFF",
            discount_type=DiscountType.PERCENT,
            value=10,
            expires_at=None,
            max_redemptions=None,
        )
    )
    await discount_service.set_active(code.id, False)

    with pytest.raises(DiscountCodeInvalidError):
        await service.create_checkout_session(
            CreateCheckoutSession(
                lines=[CartLine(item_id=item.id, variant_id=(await service.list_variants_for_item(item.id))[0].id, quantity=1)],
                customer_id=None,
                customer_email=None,
                discount_code="OFF",
            )
        )


@pytest.mark.asyncio
async def test_checkout_rejects_expired_discount_code(
    service: MarketplaceService,
    discount_service: DiscountCodeService,
) -> None:
    item = await service.create_item(_create_command())
    await discount_service.create_code(
        CreateDiscountCode(
            code="EXPIRED",
            discount_type=DiscountType.PERCENT,
            value=10,
            expires_at=NOW - timedelta(days=1),
            max_redemptions=None,
        )
    )

    with pytest.raises(DiscountCodeInvalidError):
        await service.create_checkout_session(
            CreateCheckoutSession(
                lines=[CartLine(item_id=item.id, variant_id=(await service.list_variants_for_item(item.id))[0].id, quantity=1)],
                customer_id=None,
                customer_email=None,
                discount_code="EXPIRED",
            )
        )


@pytest.mark.asyncio
async def test_checkout_rejects_exhausted_discount_code(
    service: MarketplaceService,
    discount_service: DiscountCodeService,
    discount_code_repository: InMemoryDiscountCodeRepository,
) -> None:
    item = await service.create_item(_create_command())
    code = await discount_service.create_code(
        CreateDiscountCode(
            code="LIMITED",
            discount_type=DiscountType.PERCENT,
            value=10,
            expires_at=None,
            max_redemptions=1,
        )
    )
    exhausted = replace(code, redemption_count=1)
    await discount_code_repository.update(exhausted)

    with pytest.raises(DiscountCodeInvalidError):
        await service.create_checkout_session(
            CreateCheckoutSession(
                lines=[CartLine(item_id=item.id, variant_id=(await service.list_variants_for_item(item.id))[0].id, quantity=1)],
                customer_id=None,
                customer_email=None,
                discount_code="LIMITED",
            )
        )


@pytest.mark.asyncio
async def test_webhook_completed_increments_discount_redemption_count(
    service: MarketplaceService,
    discount_service: DiscountCodeService,
    discount_code_repository: InMemoryDiscountCodeRepository,
) -> None:
    item = await service.create_item(_create_command())
    await discount_service.create_code(
        CreateDiscountCode(
            code="SAVE10",
            discount_type=DiscountType.PERCENT,
            value=10,
            expires_at=None,
            max_redemptions=None,
        )
    )
    order, _ = await service.create_checkout_session(
        CreateCheckoutSession(
            lines=[CartLine(item_id=item.id, variant_id=(await service.list_variants_for_item(item.id))[0].id, quantity=1)],
            customer_id=None,
            customer_email=None,
            discount_code="SAVE10",
        )
    )

    payload = _event_payload("checkout.session.completed", order.stripe_checkout_session_id)
    await service.handle_webhook_event(payload, _sign(payload))

    updated_code = await discount_code_repository.get_by_code("SAVE10")
    assert updated_code is not None
    assert updated_code.redemption_count == 1


@pytest.mark.asyncio
async def test_duplicate_webhook_delivery_does_not_double_increment_redemption(
    service: MarketplaceService,
    discount_service: DiscountCodeService,
    discount_code_repository: InMemoryDiscountCodeRepository,
) -> None:
    item = await service.create_item(_create_command())
    await discount_service.create_code(
        CreateDiscountCode(
            code="SAVE10",
            discount_type=DiscountType.PERCENT,
            value=10,
            expires_at=None,
            max_redemptions=None,
        )
    )
    order, _ = await service.create_checkout_session(
        CreateCheckoutSession(
            lines=[CartLine(item_id=item.id, variant_id=(await service.list_variants_for_item(item.id))[0].id, quantity=1)],
            customer_id=None,
            customer_email=None,
            discount_code="SAVE10",
        )
    )

    payload = _event_payload("checkout.session.completed", order.stripe_checkout_session_id)
    await service.handle_webhook_event(payload, _sign(payload))
    await service.handle_webhook_event(payload, _sign(payload))

    updated_code = await discount_code_repository.get_by_code("SAVE10")
    assert updated_code is not None
    assert updated_code.redemption_count == 1
