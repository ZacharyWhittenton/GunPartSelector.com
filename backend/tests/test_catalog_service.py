from datetime import UTC, datetime
from uuid import UUID

import pytest

from site_api.domain.catalog import (
    CategoryNotFoundError,
    PartCategory,
    Product,
    ProductFilter,
    ProductNotFoundError,
    ProductSort,
    StockStatus,
)
from site_api.services.catalog import CatalogService
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


@pytest.mark.asyncio
async def test_list_categories_includes_product_counts(
    catalog_service: CatalogService,
    part_category_repository: InMemoryPartCategoryRepository,
    product_repository: InMemoryProductRepository,
) -> None:
    category = _make_category()
    part_category_repository.categories.append(category)
    part_category_repository.product_counts[category.id] = 2

    entries = await catalog_service.list_categories()

    assert len(entries) == 1
    assert entries[0].product_count == 2


@pytest.mark.asyncio
async def test_get_category_by_slug_raises_when_missing(catalog_service: CatalogService) -> None:
    with pytest.raises(CategoryNotFoundError):
        await catalog_service.get_category_by_slug("does-not-exist")


@pytest.mark.asyncio
async def test_list_products_filters_by_brand(
    catalog_service: CatalogService,
    product_repository: InMemoryProductRepository,
) -> None:
    product_repository.products.append(_make_product(id=UUID(int=1), brand="BCM"))
    product_repository.products.append(_make_product(id=UUID(int=2), brand="Faxon Firearms"))

    products, total = await catalog_service.list_products(ProductFilter(brand=["BCM"]))

    assert total == 1
    assert products[0].brand == "BCM"


@pytest.mark.asyncio
async def test_list_products_filters_by_price_range(
    catalog_service: CatalogService,
    product_repository: InMemoryProductRepository,
) -> None:
    product_repository.products.append(_make_product(id=UUID(int=1), price_cents=10000))
    product_repository.products.append(_make_product(id=UUID(int=2), price_cents=50000))

    products, total = await catalog_service.list_products(
        ProductFilter(price_min_cents=20000, price_max_cents=60000)
    )

    assert total == 1
    assert products[0].price_cents == 50000


@pytest.mark.asyncio
async def test_list_products_filters_by_attribute_tags_and(
    catalog_service: CatalogService,
    product_repository: InMemoryProductRepository,
) -> None:
    product_repository.products.append(
        _make_product(id=UUID(int=1), attribute_tags=["caliber:556", "gassystem:mid"])
    )
    product_repository.products.append(
        _make_product(id=UUID(int=2), attribute_tags=["caliber:556", "gassystem:carbine"])
    )

    products, total = await catalog_service.list_products(
        ProductFilter(attribute_tags=["caliber:556", "gassystem:carbine"])
    )

    assert total == 1
    assert products[0].id == UUID(int=2)


@pytest.mark.asyncio
async def test_list_products_sorts_price_ascending(
    catalog_service: CatalogService,
    product_repository: InMemoryProductRepository,
) -> None:
    product_repository.products.append(_make_product(id=UUID(int=1), price_cents=50000))
    product_repository.products.append(_make_product(id=UUID(int=2), price_cents=10000))

    products, _ = await catalog_service.list_products(ProductFilter(sort=ProductSort.PRICE_ASC))

    assert [p.id for p in products] == [UUID(int=2), UUID(int=1)]


@pytest.mark.asyncio
async def test_list_products_sorts_by_popularity(
    catalog_service: CatalogService,
    product_repository: InMemoryProductRepository,
) -> None:
    product_repository.products.append(_make_product(id=UUID(int=1), view_count=3))
    product_repository.products.append(_make_product(id=UUID(int=2), view_count=40))

    products, _ = await catalog_service.list_products(ProductFilter(sort=ProductSort.POPULARITY))

    assert [p.id for p in products] == [UUID(int=2), UUID(int=1)]


@pytest.mark.asyncio
async def test_list_products_filters_by_retailer(
    catalog_service: CatalogService,
    product_repository: InMemoryProductRepository,
) -> None:
    product_repository.products.append(
        _make_product(id=UUID(int=1), affiliate_retailer_name="Brownells")
    )
    product_repository.products.append(
        _make_product(id=UUID(int=2), affiliate_retailer_name="MidwayUSA")
    )

    products, total = await catalog_service.list_products(ProductFilter(retailer=["Brownells"]))

    assert total == 1
    assert products[0].affiliate_retailer_name == "Brownells"


@pytest.mark.asyncio
async def test_get_product_by_slug_increments_view_count(
    catalog_service: CatalogService,
    product_repository: InMemoryProductRepository,
) -> None:
    product_repository.products.append(_make_product(id=UUID(int=1), view_count=2))

    product = await catalog_service.get_product_by_slug("bcm-standard-16in-barrel")
    assert product.view_count == 2

    stored = await product_repository.get_by_id(UUID(int=1))
    assert stored is not None
    assert stored.view_count == 3


@pytest.mark.asyncio
async def test_list_products_paginates(
    catalog_service: CatalogService,
    product_repository: InMemoryProductRepository,
) -> None:
    for n in range(5):
        product_repository.products.append(_make_product(id=UUID(int=n + 1), slug=f"product-{n}"))

    products, total = await catalog_service.list_products(ProductFilter(limit=2, offset=2))

    assert total == 5
    assert len(products) == 2


@pytest.mark.asyncio
async def test_get_product_by_slug_raises_when_missing(catalog_service: CatalogService) -> None:
    with pytest.raises(ProductNotFoundError):
        await catalog_service.get_product_by_slug("does-not-exist")


@pytest.mark.asyncio
async def test_get_category_facets_groups_tags_by_prefix(
    catalog_service: CatalogService,
    part_category_repository: InMemoryPartCategoryRepository,
    product_repository: InMemoryProductRepository,
) -> None:
    category = _make_category()
    part_category_repository.categories.append(category)
    product_repository.products.append(
        _make_product(
            id=UUID(int=1),
            category_id=category.id,
            brand="BCM",
            affiliate_retailer_name="Brownells",
            price_cents=10000,
            attribute_tags=["caliber:556", "gassystem:mid"],
        )
    )
    product_repository.products.append(
        _make_product(
            id=UUID(int=2),
            category_id=category.id,
            brand="Faxon Firearms",
            affiliate_retailer_name="MidwayUSA",
            price_cents=30000,
            attribute_tags=["caliber:300blk", "gassystem:pistol"],
        )
    )

    facets = await catalog_service.get_category_facets("barrel")

    assert facets.brands == ["BCM", "Faxon Firearms"]
    assert facets.retailers == ["Brownells", "MidwayUSA"]
    assert facets.attribute_tag_groups["caliber"] == ["300blk", "556"]
    assert facets.price_min_cents == 10000
    assert facets.price_max_cents == 30000
