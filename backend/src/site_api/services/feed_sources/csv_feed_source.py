"""Reads a local CSV export into FeedItem rows.

This is the concrete, usable-today FeedSource: point it at a CSV exported from a
retailer's own product listing (or typed up by hand) and it becomes a bulk import.
It's also the reference implementation for what a real API-backed FeedSource (e.g.
AvantLink) needs to produce -- same FeedItem shape, just sourced from an HTTP call
instead of a file.

Expected columns (header row required):
  category_hint, brand, name, sku, price_cents, weight_oz, description,
  affiliate_url, image_url, in_stock, attribute_tags

attribute_tags is semicolon-separated (e.g. "caliber:556;platform:ar15").
in_stock is "true"/"false" (case-insensitive); anything else is treated as false.
"""

import csv
from pathlib import Path

from site_api.domain.feed_import import FeedItem

REQUIRED_COLUMNS = {
    "category_hint",
    "brand",
    "name",
    "sku",
    "price_cents",
    "weight_oz",
    "description",
    "affiliate_url",
}


class CsvFeedSourceError(Exception):
    """Raised when the CSV is missing required columns or has an unparseable row."""


class CsvFeedSource:
    def __init__(self, csv_path: Path) -> None:
        self._csv_path = csv_path

    async def fetch_items(self) -> list[FeedItem]:
        with self._csv_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
            if missing:
                raise CsvFeedSourceError(f"CSV is missing required column(s): {sorted(missing)}")

            items: list[FeedItem] = []
            for row_number, row in enumerate(reader, start=2):
                try:
                    items.append(self._row_to_item(row))
                except (KeyError, ValueError) as error:
                    raise CsvFeedSourceError(f"Row {row_number}: {error}") from error
            return items

    @staticmethod
    def _row_to_item(row: dict[str, str]) -> FeedItem:
        tags_raw = row.get("attribute_tags", "") or ""
        image_url = row.get("image_url", "") or None
        return FeedItem(
            category_hint=row["category_hint"].strip(),
            brand=row["brand"].strip(),
            name=row["name"].strip(),
            sku=row["sku"].strip(),
            price_cents=int(row["price_cents"]),
            weight_oz=float(row["weight_oz"]),
            description=row["description"].strip(),
            affiliate_url=row["affiliate_url"].strip(),
            image_url=image_url,
            in_stock=(row.get("in_stock", "true") or "true").strip().lower() == "true",
            attribute_tags=[tag.strip() for tag in tags_raw.split(";") if tag.strip()],
        )
