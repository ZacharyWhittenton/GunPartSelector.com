from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient

from site_api.domain.catalog import Product, StockStatus
from tests.conftest import InMemoryProductRepository

NOW = datetime(2026, 8, 15, 12, 0, tzinfo=UTC)


def _make_product(**overrides: object) -> Product:
    defaults: dict[str, object] = {
        "id": UUID(int=10),
        "category_id": UUID(int=1),
        "brand": "BCM",
        "name": "Standard 16in Barrel",
        "slug": "bcm-standard-16in-barrel",
        "sku": "BCM-BBL-16",
        "description": "A test barrel.",
        "price_cents": 22900,
        "weight_oz": 28.5,
        "image_url": None,
        "affiliate_url": "#",
        "affiliate_retailer_name": None,
        "stock_status": StockStatus.IN_STOCK,
        "attribute_tags": ["caliber:556"],
        "is_active": True,
        "created_at": NOW,
        "updated_at": NOW,
    }
    defaults.update(overrides)
    return Product(**defaults)


def test_create_build_returns_slug_and_items(
    client: TestClient,
    product_repository: InMemoryProductRepository,
) -> None:
    product_repository.products.append(_make_product())

    response = client.post(
        "/api/builds",
        json={"name": "My Carbine", "items": [{"productId": str(UUID(int=10)), "quantity": 2}]},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "My Carbine"
    assert len(body["slug"]) == 10
    assert body["items"][0]["product"]["slug"] == "bcm-standard-16in-barrel"
    assert body["items"][0]["quantity"] == 2


def test_create_build_rejects_empty_items(client: TestClient) -> None:
    response = client.post("/api/builds", json={"name": None, "items": []})

    assert response.status_code == 422


def test_create_build_returns_404_for_missing_product(client: TestClient) -> None:
    response = client.post(
        "/api/builds",
        json={"name": None, "items": [{"productId": str(UUID(int=999)), "quantity": 1}]},
    )

    assert response.status_code == 404


def test_get_build_by_slug_round_trips(
    client: TestClient,
    product_repository: InMemoryProductRepository,
) -> None:
    product_repository.products.append(_make_product())
    create_response = client.post(
        "/api/builds",
        json={"name": None, "items": [{"productId": str(UUID(int=10)), "quantity": 1}]},
    )
    slug = create_response.json()["slug"]

    response = client.get(f"/api/builds/{slug}")

    assert response.status_code == 200
    assert response.json()["items"][0]["product"]["slug"] == "bcm-standard-16in-barrel"


def test_get_build_by_slug_returns_404_when_missing(client: TestClient) -> None:
    response = client.get("/api/builds/does-not-exist")

    assert response.status_code == 404
