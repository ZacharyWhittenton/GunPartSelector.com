from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient

from site_api.domain.catalog import PartCategory, Product, StockStatus
from tests.conftest import InMemoryPartCategoryRepository, InMemoryProductRepository

NOW = datetime(2026, 8, 15, 12, 0, tzinfo=UTC)


def _make_category(**overrides: object) -> PartCategory:
    defaults: dict[str, object] = {
        "id": UUID(int=1),
        "slug": "barrel",
        "name": "Barrel",
        "section": "upper",
        "sort_order": 1,
        "created_at": NOW,
    }
    defaults.update(overrides)
    return PartCategory(**defaults)


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
        "attribute_tags": ["caliber:556", "gassystem:mid"],
        "view_count": 0,
        "is_active": True,
        "created_at": NOW,
        "updated_at": NOW,
    }
    defaults.update(overrides)
    return Product(**defaults)


def test_list_categories_returns_product_counts(
    client: TestClient,
    part_category_repository: InMemoryPartCategoryRepository,
) -> None:
    category = _make_category()
    part_category_repository.categories.append(category)
    part_category_repository.product_counts[category.id] = 3

    response = client.get("/api/catalog/categories")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["slug"] == "barrel"
    assert body[0]["productCount"] == 3


def test_list_products_returns_paginated_response(
    client: TestClient,
    product_repository: InMemoryProductRepository,
) -> None:
    product_repository.products.append(_make_product())

    response = client.get("/api/catalog/products")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["limit"] == 24
    assert body["offset"] == 0
    assert body["items"][0]["slug"] == "bcm-standard-16in-barrel"


def test_list_products_filters_by_brand_query_param(
    client: TestClient,
    product_repository: InMemoryProductRepository,
) -> None:
    product_repository.products.append(_make_product(id=UUID(int=1), brand="BCM"))
    product_repository.products.append(
        _make_product(id=UUID(int=2), slug="other-barrel", brand="Faxon Firearms")
    )

    response = client.get("/api/catalog/products", params={"brand": "BCM"})

    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["brand"] == "BCM"


def test_list_products_filters_by_retailer_query_param(
    client: TestClient,
    product_repository: InMemoryProductRepository,
) -> None:
    product_repository.products.append(
        _make_product(id=UUID(int=1), affiliate_retailer_name="Brownells")
    )
    product_repository.products.append(
        _make_product(id=UUID(int=2), slug="other-barrel", affiliate_retailer_name="MidwayUSA")
    )

    response = client.get("/api/catalog/products", params={"retailer": "Brownells"})

    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["brand"] == "BCM"


def test_list_products_sorts_by_popularity_query_param(
    client: TestClient,
    product_repository: InMemoryProductRepository,
) -> None:
    product_repository.products.append(_make_product(id=UUID(int=1), view_count=1))
    product_repository.products.append(
        _make_product(id=UUID(int=2), slug="other-barrel", view_count=50)
    )

    response = client.get("/api/catalog/products", params={"sort": "popularity"})

    body = response.json()
    assert body["items"][0]["slug"] == "other-barrel"


def test_get_product_by_slug_returns_detail(
    client: TestClient,
    product_repository: InMemoryProductRepository,
) -> None:
    product_repository.products.append(_make_product())

    response = client.get("/api/catalog/products/bcm-standard-16in-barrel")

    assert response.status_code == 200
    body = response.json()
    assert body["sku"] == "BCM-BBL-16"
    assert body["affiliateUrl"] == "#"


def test_get_product_by_slug_returns_404_when_missing(client: TestClient) -> None:
    response = client.get("/api/catalog/products/does-not-exist")

    assert response.status_code == 404


def test_get_category_facets_returns_grouped_tags(
    client: TestClient,
    part_category_repository: InMemoryPartCategoryRepository,
    product_repository: InMemoryProductRepository,
) -> None:
    category = _make_category()
    part_category_repository.categories.append(category)
    product_repository.products.append(
        _make_product(category_id=category.id, affiliate_retailer_name="Brownells")
    )

    response = client.get("/api/catalog/categories/barrel/facets")

    assert response.status_code == 200
    body = response.json()
    assert body["brands"] == ["BCM"]
    assert body["retailers"] == ["Brownells"]
    assert body["attributeTagGroups"]["caliber"] == ["556"]
