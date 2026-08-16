import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from site_api.domain.builds import (
    Build,
    BuildItem,
    BuildNotFoundError,
    BuildRepository,
    EmptyBuildError,
)
from site_api.domain.catalog import ProductNotFoundError, ProductRepository

SLUG_ALPHABET = "abcdefghijkmnopqrstuvwxyz23456789"
SLUG_LENGTH = 10


@dataclass(frozen=True, slots=True)
class CreateBuildItem:
    product_id: UUID
    quantity: int


@dataclass(frozen=True, slots=True)
class CreateBuild:
    name: str | None
    items: list[CreateBuildItem]


class BuildService:
    def __init__(
        self,
        build_repository: BuildRepository,
        product_repository: ProductRepository,
        id_factory: Callable[[], UUID] = uuid4,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._builds = build_repository
        self._products = product_repository
        self._id_factory = id_factory
        self._clock = clock

    async def create_build(self, command: CreateBuild) -> Build:
        if not command.items:
            raise EmptyBuildError

        build_id = self._id_factory()
        items: list[BuildItem] = []
        for line in command.items:
            product = await self._products.get_by_id(line.product_id)
            if product is None or not product.is_active:
                raise ProductNotFoundError

            items.append(
                BuildItem(
                    id=self._id_factory(),
                    build_id=build_id,
                    product=product,
                    quantity=line.quantity,
                )
            )

        slug = await self._unique_slug()
        build = Build(
            id=build_id,
            slug=slug,
            name=command.name,
            created_at=self._clock(),
            items=items,
        )
        await self._builds.add(build)
        return build

    async def get_build_by_slug(self, slug: str) -> Build:
        build = await self._builds.get_by_slug(slug)
        if build is None:
            raise BuildNotFoundError
        return build

    async def _unique_slug(self) -> str:
        while True:
            slug = "".join(secrets.choice(SLUG_ALPHABET) for _ in range(SLUG_LENGTH))
            if not await self._builds.slug_exists(slug):
                return slug
