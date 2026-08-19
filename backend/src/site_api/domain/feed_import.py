"""Normalized shape for ingesting a retailer product feed.

The catalog currently has no real retailer datafeed connected -- every product is
original placeholder data (see data/seeds/seed_catalog_data.py). This module defines
the extension point for when one does: any retailer-specific feed (a CSV export, an
AvantLink datafeed API response, etc.) gets adapted into a list of FeedItem, and
FeedImportService (services/feed_import.py) upserts those into the catalog the same
way regardless of where they came from.

To add a real feed source (e.g. once an AvantLink application is approved):
  1. Implement FeedSource for it -- a class with async fetch_items() -> list[FeedItem].
  2. Point data/seeds/import_feed.py at it instead of CsvFeedSource.
Nothing else in the import path changes.
"""

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class FeedItem:
    """One product offer from a retailer feed, already normalized to our shape.

    Deliberately has no `retailer` field: a FeedSource represents one retailer's
    feed (or one batch of it), and the caller passes that retailer name once to
    FeedImportService.import_items() rather than repeating it on every row."""

    category_hint: str
    brand: str
    name: str
    sku: str
    price_cents: int
    weight_oz: float
    description: str
    affiliate_url: str
    image_url: str | None = None
    in_stock: bool = True
    attribute_tags: list[str] = field(default_factory=list)


class FeedSource(Protocol):
    """Anything that can produce a batch of normalized feed items."""

    async def fetch_items(self) -> list[FeedItem]: ...


@dataclass(frozen=True, slots=True)
class FeedImportResult:
    retailer: str
    created: int
    updated: int
    skipped_unmapped_category: list[str]
