from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from site_api.domain.catalog import Product


@dataclass(frozen=True, slots=True)
class BuildItem:
    id: UUID
    build_id: UUID
    product: Product
    quantity: int


@dataclass(frozen=True, slots=True)
class Build:
    id: UUID
    slug: str
    name: str | None
    created_at: datetime
    items: list[BuildItem]


class BuildNotFoundError(Exception):
    """Raised when a referenced build does not exist."""


class EmptyBuildError(Exception):
    """Raised when a build is created with no items."""


class BuildRepository(Protocol):
    async def add(self, build: Build) -> None: ...

    async def slug_exists(self, slug: str) -> bool: ...

    async def get_by_slug(self, slug: str) -> Build | None: ...
