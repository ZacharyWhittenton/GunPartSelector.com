from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from site_api.api.dependencies import get_catalog_service
from site_api.api.schemas import PaginatedResponse
from site_api.domain.catalog import (
    CategoryNotFoundError,
    CategoryWithCount,
    Product,
    ProductFacets,
    ProductFilter,
    ProductNotFoundError,
    ProductSort,
    StockStatus,
)
from site_api.services.catalog import CatalogService

router = APIRouter(prefix="/catalog", tags=["catalog"])


class CategorySummary(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: UUID
    slug: str
    name: str
    section: str
    product_count: int


class FacetsResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    brands: list[str]
    attribute_tag_groups: dict[str, list[str]]
    price_min_cents: int
    price_max_cents: int


class ProductSummary(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: UUID
    category_id: UUID
    brand: str
    name: str
    slug: str
    price_cents: int
    weight_oz: float
    image_url: str | None
    stock_status: str
    attribute_tags: list[str]


class ProductDetail(ProductSummary):
    sku: str | None
    description: str
    affiliate_url: str
    affiliate_retailer_name: str | None


def to_category_summary(entry: CategoryWithCount) -> CategorySummary:
    return CategorySummary(
        id=entry.category.id,
        slug=entry.category.slug,
        name=entry.category.name,
        section=entry.category.section,
        product_count=entry.product_count,
    )


def to_product_summary(product: Product) -> ProductSummary:
    return ProductSummary(
        id=product.id,
        category_id=product.category_id,
        brand=product.brand,
        name=product.name,
        slug=product.slug,
        price_cents=product.price_cents,
        weight_oz=product.weight_oz,
        image_url=product.image_url,
        stock_status=product.stock_status.value,
        attribute_tags=product.attribute_tags,
    )


def to_product_detail(product: Product) -> ProductDetail:
    return ProductDetail(
        **to_product_summary(product).model_dump(),
        sku=product.sku,
        description=product.description,
        affiliate_url=product.affiliate_url,
        affiliate_retailer_name=product.affiliate_retailer_name,
    )


def to_facets_response(facets: ProductFacets) -> FacetsResponse:
    return FacetsResponse(
        brands=facets.brands,
        attribute_tag_groups=facets.attribute_tag_groups,
        price_min_cents=facets.price_min_cents,
        price_max_cents=facets.price_max_cents,
    )


@router.get("/categories", response_model=list[CategorySummary], response_model_by_alias=True)
async def list_categories(
    service: Annotated[CatalogService, Depends(get_catalog_service)],
) -> list[CategorySummary]:
    categories = await service.list_categories()
    return [to_category_summary(entry) for entry in categories]


@router.get(
    "/categories/{slug}/facets", response_model=FacetsResponse, response_model_by_alias=True
)
async def get_category_facets(
    slug: str,
    service: Annotated[CatalogService, Depends(get_catalog_service)],
) -> FacetsResponse:
    try:
        facets = await service.get_category_facets(slug)
    except CategoryNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        ) from error

    return to_facets_response(facets)


@router.get("/categories/{slug}", response_model=CategorySummary, response_model_by_alias=True)
async def get_category(
    slug: str,
    service: Annotated[CatalogService, Depends(get_catalog_service)],
) -> CategorySummary:
    categories = await service.list_categories()
    for entry in categories:
        if entry.category.slug == slug:
            return to_category_summary(entry)

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")


@router.get(
    "/products", response_model=PaginatedResponse[ProductSummary], response_model_by_alias=True
)
async def list_products(
    service: Annotated[CatalogService, Depends(get_catalog_service)],
    category: str | None = None,
    brand: Annotated[list[str] | None, Query()] = None,
    price_min: Annotated[int | None, Query(alias="priceMin")] = None,
    price_max: Annotated[int | None, Query(alias="priceMax")] = None,
    stock: StockStatus | None = None,
    tag: Annotated[list[str] | None, Query()] = None,
    sort: ProductSort = ProductSort.NEWEST,
    limit: Annotated[int, Query(le=100, ge=1)] = 24,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PaginatedResponse[ProductSummary]:
    products, total = await service.list_products(
        ProductFilter(
            category_slug=category,
            brand=brand,
            price_min_cents=price_min,
            price_max_cents=price_max,
            stock_status=stock,
            attribute_tags=tag,
            sort=sort,
            limit=limit,
            offset=offset,
        )
    )
    return PaginatedResponse[ProductSummary](
        items=[to_product_summary(product) for product in products],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/products/{slug}", response_model=ProductDetail, response_model_by_alias=True)
async def get_product(
    slug: str,
    service: Annotated[CatalogService, Depends(get_catalog_service)],
) -> ProductDetail:
    try:
        product = await service.get_product_by_slug(slug)
    except ProductNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        ) from error

    return to_product_detail(product)
