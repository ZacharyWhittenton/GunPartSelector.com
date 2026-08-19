from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID


class StockStatus(StrEnum):
    IN_STOCK = "in_stock"
    OUT_OF_STOCK = "out_of_stock"
    UNKNOWN = "unknown"


class ProductSort(StrEnum):
    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"
    NAME_ASC = "name_asc"
    NEWEST = "newest"
    POPULARITY = "popularity"


@dataclass(frozen=True, slots=True)
class PartCategory:
    id: UUID
    slug: str
    name: str
    section: str
    sort_order: int
    created_at: datetime


@dataclass(frozen=True, slots=True)
class CategoryWithCount:
    category: PartCategory
    product_count: int


@dataclass(frozen=True, slots=True)
class Product:
    id: UUID
    category_id: UUID
    brand: str
    name: str
    slug: str
    sku: str | None
    description: str
    price_cents: int
    weight_oz: float
    image_url: str | None
    affiliate_url: str
    affiliate_retailer_name: str | None
    stock_status: StockStatus
    attribute_tags: list[str]
    view_count: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ProductFacets:
    brands: list[str]
    retailers: list[str]
    attribute_tag_groups: dict[str, list[str]]
    price_min_cents: int
    price_max_cents: int


@dataclass(frozen=True, slots=True)
class ProductFilter:
    category_slug: str | None = None
    brand: list[str] | None = None
    retailer: list[str] | None = None
    price_min_cents: int | None = None
    price_max_cents: int | None = None
    stock_status: StockStatus | None = None
    attribute_tags: list[str] | None = None
    search: str | None = None
    sort: ProductSort = ProductSort.NEWEST
    limit: int = 24
    offset: int = 0


class CategoryNotFoundError(Exception):
    """Raised when a referenced part category does not exist."""


class ProductNotFoundError(Exception):
    """Raised when a referenced product does not exist."""


class PartCategoryRepository(Protocol):
    async def list_with_counts(self) -> list[CategoryWithCount]: ...

    async def get_by_slug(self, slug: str) -> PartCategory | None: ...


class ProductRepository(Protocol):
    async def list_filtered(self, product_filter: ProductFilter) -> tuple[list[Product], int]: ...

    async def get_by_slug(self, slug: str) -> Product | None: ...

    async def get_by_id(self, product_id: UUID) -> Product | None: ...

    async def list_distinct_facets(self, category_id: UUID) -> ProductFacets: ...

    async def increment_view_count(self, product_id: UUID) -> None: ...
