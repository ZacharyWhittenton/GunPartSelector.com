import hashlib
import hmac
import json
import time
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from site_api.domain.discount_codes import DiscountCode, DiscountType
from site_api.domain.marketplace import ItemVariant, MarketplaceItem, VariantStockStatus
from tests.conftest import InMemoryDiscountCodeRepository, InMemoryMarketplaceItemRepository

WEBHOOK_SECRET = "whsec_test_secret"


def _register(client: TestClient, email: str, full_name: str = "Test User") -> dict:
    response = client.post(
        "/api/auth/register",
        json={"emailAddress": email, "fullName": full_name, "password": "super-secret-1"},
    )
    assert response.status_code == 201
    return response.json()


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _sign(payload: bytes, secret: str = WEBHOOK_SECRET) -> str:
    ts = int(time.time())
    signed_payload = f"{ts}.{payload.decode()}"
    signature = hmac.new(secret.encode(), signed_payload.encode(), hashlib.sha256).hexdigest()
    return f"t={ts},v1={signature}"


def _event_payload(event_type: str, session_id: str) -> bytes:
    body = {
        "id": "evt_test_1",
        "object": "event",
        "type": event_type,
        "data": {
            "object": {
                "id": session_id,
                "object": "checkout.session",
                "payment_intent": "pi_test_1",
                "customer_details": {"email": "guest@example.com"},
            }
        },
    }
    return json.dumps(body).encode()


def _make_item(**overrides: object) -> MarketplaceItem:
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    defaults: dict[str, object] = {
        "id": UUID(int=1),
        "name": "Website Audit",
        "slug": "website-audit",
        "description": "A full technical and SEO audit.",
        "price_cents": 5000,
        "image_url": None,
        "is_active": True,
        "created_by_admin_id": UUID(int=100),
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return MarketplaceItem(**defaults)


def _make_variant(**overrides: object) -> ItemVariant:
    now = datetime.now(UTC)
    defaults: dict[str, object] = {
        "id": UUID(int=1000),
        "marketplace_item_id": UUID(int=1),
        "label": "One Size",
        "sort_order": 0,
        "stock_status": VariantStockStatus.IN_STOCK,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return ItemVariant(**defaults)


def test_list_items_only_returns_active(
    client: TestClient,
    marketplace_item_repository: InMemoryMarketplaceItemRepository,
) -> None:
    marketplace_item_repository.items.append(_make_item())
    marketplace_item_repository.items.append(
        _make_item(id=UUID(int=2), slug="inactive-item", is_active=False)
    )

    response = client.get("/api/marketplace/items")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["slug"] == "website-audit"


def test_get_item_by_slug_404_when_missing(client: TestClient) -> None:
    response = client.get("/api/marketplace/items/does-not-exist")

    assert response.status_code == 404


def test_get_item_by_slug_success(
    client: TestClient,
    marketplace_item_repository: InMemoryMarketplaceItemRepository,
) -> None:
    marketplace_item_repository.items.append(_make_item())

    response = client.get("/api/marketplace/items/website-audit")

    assert response.status_code == 200
    assert response.json()["priceCents"] == 5000


def test_checkout_as_guest_returns_checkout_url(
    client: TestClient,
    marketplace_item_repository: InMemoryMarketplaceItemRepository,
) -> None:
    marketplace_item_repository.items.append(_make_item())
    marketplace_item_repository.variants.append(_make_variant())

    response = client.post(
        "/api/marketplace/checkout",
        json={
            "items": [
                {"itemId": str(UUID(int=1)), "variantId": str(UUID(int=1000)), "quantity": 1}
            ]
        },
    )

    assert response.status_code == 200
    assert response.json()["checkoutUrl"].startswith("https://checkout.stripe.com/")


def test_checkout_rejects_empty_cart(client: TestClient) -> None:
    response = client.post("/api/marketplace/checkout", json={"items": []})

    assert response.status_code == 422


def test_checkout_rejects_unknown_item(client: TestClient) -> None:
    response = client.post(
        "/api/marketplace/checkout",
        json={
            "items": [
                {"itemId": str(UUID(int=999)), "variantId": str(UUID(int=1000)), "quantity": 1}
            ]
        },
    )

    assert response.status_code == 404


def test_checkout_rejects_inactive_item(
    client: TestClient,
    marketplace_item_repository: InMemoryMarketplaceItemRepository,
) -> None:
    marketplace_item_repository.items.append(_make_item(is_active=False))

    response = client.post(
        "/api/marketplace/checkout",
        json={
            "items": [
                {"itemId": str(UUID(int=1)), "variantId": str(UUID(int=1000)), "quantity": 1}
            ]
        },
    )

    assert response.status_code == 409


def _make_discount_code(**overrides: object) -> DiscountCode:
    now = datetime.now(UTC)
    defaults: dict[str, object] = {
        "id": UUID(int=500),
        "code": "SAVE10",
        "discount_type": DiscountType.PERCENT,
        "value": 10,
        "is_active": True,
        "expires_at": None,
        "max_redemptions": None,
        "redemption_count": 0,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    return DiscountCode(**defaults)


def test_checkout_with_valid_discount_code_succeeds(
    client: TestClient,
    marketplace_item_repository: InMemoryMarketplaceItemRepository,
    discount_code_repository: InMemoryDiscountCodeRepository,
) -> None:
    marketplace_item_repository.items.append(_make_item())
    marketplace_item_repository.variants.append(_make_variant())
    discount_code_repository.discount_codes.append(_make_discount_code())

    response = client.post(
        "/api/marketplace/checkout",
        json={
            "items": [
                {"itemId": str(UUID(int=1)), "variantId": str(UUID(int=1000)), "quantity": 1}
            ],
            "discountCode": "save10",
        },
    )

    assert response.status_code == 200
    assert response.json()["checkoutUrl"].startswith("https://checkout.stripe.com/")


def test_checkout_rejects_unknown_discount_code(
    client: TestClient,
    marketplace_item_repository: InMemoryMarketplaceItemRepository,
) -> None:
    marketplace_item_repository.items.append(_make_item())
    marketplace_item_repository.variants.append(_make_variant())

    response = client.post(
        "/api/marketplace/checkout",
        json={
            "items": [
                {"itemId": str(UUID(int=1)), "variantId": str(UUID(int=1000)), "quantity": 1}
            ],
            "discountCode": "MISSING",
        },
    )

    assert response.status_code == 400


def test_checkout_rejects_expired_discount_code(
    client: TestClient,
    marketplace_item_repository: InMemoryMarketplaceItemRepository,
    discount_code_repository: InMemoryDiscountCodeRepository,
) -> None:
    marketplace_item_repository.items.append(_make_item())
    marketplace_item_repository.variants.append(_make_variant())
    discount_code_repository.discount_codes.append(
        _make_discount_code(expires_at=datetime.now(UTC) - timedelta(days=1))
    )

    response = client.post(
        "/api/marketplace/checkout",
        json={
            "items": [
                {"itemId": str(UUID(int=1)), "variantId": str(UUID(int=1000)), "quantity": 1}
            ],
            "discountCode": "SAVE10",
        },
    )

    assert response.status_code == 400


def test_webhook_requires_signature_header(client: TestClient) -> None:
    response = client.post("/api/marketplace/webhook", content=b"{}")

    assert response.status_code == 400


def test_webhook_rejects_invalid_signature(client: TestClient) -> None:
    payload = _event_payload("checkout.session.completed", "cs_test_1")

    response = client.post(
        "/api/marketplace/webhook",
        content=payload,
        headers={"Stripe-Signature": "t=1,v1=deadbeef"},
    )

    assert response.status_code == 400


def test_webhook_updates_order_status_and_is_visible_by_session(
    client: TestClient,
    marketplace_item_repository: InMemoryMarketplaceItemRepository,
) -> None:
    marketplace_item_repository.items.append(_make_item())
    marketplace_item_repository.variants.append(_make_variant())
    checkout_response = client.post(
        "/api/marketplace/checkout",
        json={
            "items": [
                {"itemId": str(UUID(int=1)), "variantId": str(UUID(int=1000)), "quantity": 1}
            ]
        },
    )
    assert checkout_response.status_code == 200

    session_id = "cs_test_1"
    payload = _event_payload("checkout.session.completed", session_id)
    webhook_response = client.post(
        "/api/marketplace/webhook",
        content=payload,
        headers={"Stripe-Signature": _sign(payload)},
    )
    assert webhook_response.status_code == 200

    order_response = client.get(f"/api/marketplace/orders/by-session/{session_id}")
    assert order_response.status_code == 200
    assert order_response.json()["status"] == "paid"


def test_get_order_by_session_404_when_missing(client: TestClient) -> None:
    response = client.get("/api/marketplace/orders/by-session/cs_missing")

    assert response.status_code == 404


def test_list_my_orders_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/marketplace/orders/mine")

    assert response.status_code == 401


def test_list_my_orders_returns_only_own(
    client: TestClient,
    marketplace_item_repository: InMemoryMarketplaceItemRepository,
) -> None:
    marketplace_item_repository.items.append(_make_item())
    marketplace_item_repository.variants.append(_make_variant())
    owner = _register(client, "owner@example.com")
    other = _register(client, "other@example.com")

    client.post(
        "/api/marketplace/checkout",
        json={
            "items": [
                {"itemId": str(UUID(int=1)), "variantId": str(UUID(int=1000)), "quantity": 1}
            ]
        },
        headers=_auth_headers(owner["accessToken"]),
    )

    response = client.get(
        "/api/marketplace/orders/mine",
        headers=_auth_headers(other["accessToken"]),
    )

    assert response.status_code == 200
    assert response.json() == []


def test_wishlist_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/marketplace/wishlist")

    assert response.status_code == 401


def test_wishlist_add_list_remove(
    client: TestClient,
    marketplace_item_repository: InMemoryMarketplaceItemRepository,
) -> None:
    marketplace_item_repository.items.append(_make_item())
    user = _register(client, "customer@example.com")
    headers = _auth_headers(user["accessToken"])

    add_response = client.post(
        "/api/marketplace/wishlist",
        json={"itemId": str(UUID(int=1))},
        headers=headers,
    )
    assert add_response.status_code == 201

    list_response = client.get("/api/marketplace/wishlist", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    remove_response = client.delete(
        f"/api/marketplace/wishlist/{UUID(int=1)}",
        headers=headers,
    )
    assert remove_response.status_code == 204

    empty_response = client.get("/api/marketplace/wishlist", headers=headers)
    assert empty_response.json() == []


def test_wishlist_add_unknown_item_404(client: TestClient) -> None:
    user = _register(client, "customer@example.com")

    response = client.post(
        "/api/marketplace/wishlist",
        json={"itemId": str(UUID(int=999))},
        headers=_auth_headers(user["accessToken"]),
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_checkout_unconfigured_returns_503(
    client: TestClient,
    marketplace_item_repository: InMemoryMarketplaceItemRepository,
) -> None:
    from site_api.api.dependencies import get_marketplace_service
    from site_api.services.marketplace import MarketplaceService

    marketplace_item_repository.items.append(_make_item())

    async def _unconfigured_override() -> MarketplaceService:
        from tests.conftest import InMemoryOrderRepository, InMemoryWishlistRepository

        return MarketplaceService(
            marketplace_item_repository,
            InMemoryOrderRepository(),
            InMemoryWishlistRepository(),
            None,
            None,
            "usd",
            "http://localhost:4200/marketplace/success?session_id={CHECKOUT_SESSION_ID}",
            "http://localhost:4200/cart",
        )

    client.app.dependency_overrides[get_marketplace_service] = _unconfigured_override
    try:
        response = client.post(
            "/api/marketplace/checkout",
            json={
            "items": [
                {"itemId": str(UUID(int=1)), "variantId": str(UUID(int=1000)), "quantity": 1}
            ]
        },
        )
    finally:
        del client.app.dependency_overrides[get_marketplace_service]

    assert response.status_code == 503
