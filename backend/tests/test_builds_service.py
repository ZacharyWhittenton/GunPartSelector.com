from datetime import UTC, datetime
from itertools import count
from uuid import UUID

import pytest

from site_api.domain.builds import BuildNotFoundError, EmptyBuildError
from site_api.domain.catalog import Product, ProductNotFoundError, StockStatus
from site_api.services.builds import BuildService, CreateBuild, CreateBuildItem
from tests.conftest import InMemoryBuildRepository, InMemoryProductRepository

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


@pytest.fixture
def service(
    build_repository: InMemoryBuildRepository,
    product_repository: InMemoryProductRepository,
) -> BuildService:
    ids = iter(UUID(int=n) for n in count(100))
    return BuildService(
        build_repository,
        product_repository,
        id_factory=lambda: next(ids),
        clock=lambda: NOW,
    )


@pytest.mark.asyncio
async def test_create_build_raises_when_empty(service: BuildService) -> None:
    with pytest.raises(EmptyBuildError):
        await service.create_build(CreateBuild(name=None, items=[]))


@pytest.mark.asyncio
async def test_create_build_raises_when_product_missing(service: BuildService) -> None:
    with pytest.raises(ProductNotFoundError):
        await service.create_build(
            CreateBuild(name=None, items=[CreateBuildItem(product_id=UUID(int=999), quantity=1)])
        )


@pytest.mark.asyncio
async def test_create_build_raises_when_product_inactive(
    service: BuildService,
    product_repository: InMemoryProductRepository,
) -> None:
    product_repository.products.append(_make_product(is_active=False))

    with pytest.raises(ProductNotFoundError):
        await service.create_build(
            CreateBuild(name=None, items=[CreateBuildItem(product_id=UUID(int=10), quantity=1)])
        )


@pytest.mark.asyncio
async def test_create_build_generates_slug_and_persists_items(
    service: BuildService,
    product_repository: InMemoryProductRepository,
    build_repository: InMemoryBuildRepository,
) -> None:
    product_repository.products.append(_make_product())

    build = await service.create_build(
        CreateBuild(
            name="My Carbine",
            items=[CreateBuildItem(product_id=UUID(int=10), quantity=2)],
        )
    )

    assert build.name == "My Carbine"
    assert len(build.slug) == 10
    assert len(build.items) == 1
    assert build.items[0].product.id == UUID(int=10)
    assert build.items[0].quantity == 2
    assert len(build_repository.builds) == 1


@pytest.mark.asyncio
async def test_get_build_by_slug_raises_when_missing(service: BuildService) -> None:
    with pytest.raises(BuildNotFoundError):
        await service.get_build_by_slug("does-not-exist")


@pytest.mark.asyncio
async def test_get_build_by_slug_returns_created_build(
    service: BuildService,
    product_repository: InMemoryProductRepository,
) -> None:
    product_repository.products.append(_make_product())
    created = await service.create_build(
        CreateBuild(name=None, items=[CreateBuildItem(product_id=UUID(int=10), quantity=1)])
    )

    fetched = await service.get_build_by_slug(created.slug)

    assert fetched.slug == created.slug
    assert fetched.items[0].product.slug == "bcm-standard-16in-barrel"
