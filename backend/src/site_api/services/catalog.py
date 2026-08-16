from site_api.domain.catalog import (
    CategoryNotFoundError,
    CategoryWithCount,
    PartCategory,
    PartCategoryRepository,
    Product,
    ProductFacets,
    ProductFilter,
    ProductNotFoundError,
    ProductRepository,
)


class CatalogService:
    def __init__(
        self,
        category_repository: PartCategoryRepository,
        product_repository: ProductRepository,
    ) -> None:
        self._categories = category_repository
        self._products = product_repository

    async def list_categories(self) -> list[CategoryWithCount]:
        return await self._categories.list_with_counts()

    async def get_category_by_slug(self, slug: str) -> PartCategory:
        category = await self._categories.get_by_slug(slug)
        if category is None:
            raise CategoryNotFoundError
        return category

    async def list_products(self, product_filter: ProductFilter) -> tuple[list[Product], int]:
        return await self._products.list_filtered(product_filter)

    async def get_product_by_slug(self, slug: str) -> Product:
        product = await self._products.get_by_slug(slug)
        if product is None:
            raise ProductNotFoundError
        return product

    async def get_category_facets(self, slug: str) -> ProductFacets:
        category = await self.get_category_by_slug(slug)
        return await self._products.list_distinct_facets(category.id)
