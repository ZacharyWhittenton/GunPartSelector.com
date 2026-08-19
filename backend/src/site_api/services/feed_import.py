"""Upserts normalized retailer feed items into the catalog.

Writes directly against ProductRecord/PartCategoryRecord (the same pattern
data/seeds/seed_catalog_data.py uses) rather than through the ProductRepository
Protocol, which is currently read-only -- adding write methods to that Protocol's
public contract is a bigger change than this scaffold needs. If the catalog's write
path grows beyond seeding/importing, that read-only assumption is worth revisiting.
"""

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from site_api.core.slugify import slugify
from site_api.db.models import PartCategoryRecord, ProductRecord
from site_api.domain.feed_import import FeedImportResult, FeedItem


class FeedImportService:
    def __init__(self, session: AsyncSession, category_hint_map: dict[str, str]) -> None:
        """category_hint_map maps a feed's own category label (e.g. "Barrels") to
        one of our category slugs (e.g. "barrel"). Items whose category_hint isn't
        in this map are skipped rather than guessed at."""
        self._session = session
        self._category_hint_map = category_hint_map

    async def import_items(self, retailer: str, items: list[FeedItem]) -> FeedImportResult:
        category_ids = await self._load_category_ids()

        created = 0
        updated = 0
        skipped: list[str] = []

        for item in items:
            category_slug = self._category_hint_map.get(item.category_hint)
            category_id = category_ids.get(category_slug) if category_slug else None
            if category_id is None:
                skipped.append(f"{item.name} (category_hint={item.category_hint!r})")
                continue

            slug = slugify(f"{item.brand} {item.name}")
            existing = await self._session.execute(
                select(ProductRecord).where(ProductRecord.slug == slug)
            )
            record = existing.scalar_one_or_none()

            if record is not None:
                record.category_id = category_id
                record.price_cents = item.price_cents
                record.weight_oz = item.weight_oz
                record.description = item.description
                record.image_url = item.image_url
                record.affiliate_url = item.affiliate_url
                record.affiliate_retailer_name = retailer
                record.stock_status = "in_stock" if item.in_stock else "out_of_stock"
                record.attribute_tags = item.attribute_tags
                updated += 1
                continue

            self._session.add(
                ProductRecord(
                    id=uuid4(),
                    category_id=category_id,
                    brand=item.brand,
                    name=item.name,
                    slug=slug,
                    sku=item.sku,
                    description=item.description,
                    price_cents=item.price_cents,
                    weight_oz=item.weight_oz,
                    image_url=item.image_url,
                    affiliate_url=item.affiliate_url,
                    affiliate_retailer_name=retailer,
                    stock_status="in_stock" if item.in_stock else "out_of_stock",
                    attribute_tags=item.attribute_tags,
                    is_active=True,
                )
            )
            created += 1

        await self._session.flush()
        return FeedImportResult(
            retailer=retailer, created=created, updated=updated, skipped_unmapped_category=skipped
        )

    async def _load_category_ids(self) -> dict[str, object]:
        result = await self._session.execute(select(PartCategoryRecord))
        return {record.slug: record.id for record in result.scalars().all()}
