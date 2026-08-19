"""Bulk-import a retailer's product feed (CSV today, a real API adapter later) into
the parts catalog.

This is the concrete on-ramp for the affiliate program work: once a retailer
approves an application and hands over a product feed, export/convert it to the CSV
shape documented in site_api.services.feed_sources.csv_feed_source and run this
script. No catalog code changes needed for a new retailer -- only the
CATEGORY_HINT_MAP below if that retailer's own category labels don't match ours.

To add a live API feed (e.g. AvantLink) instead of a CSV file: implement
FeedSource (site_api.domain.feed_import) with an async fetch_items() that calls
their API, then swap CsvFeedSource for it below. FeedImportService and everything
after it is unchanged.

Usage, from backend/:
    uv run python ../data/seeds/import_feed.py <csv_path> <retailer_name>

Example:
    uv run python ../data/seeds/import_feed.py ./brownells_feed.csv "Brownells"
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend" / "src"))

from site_api.core.config import Settings
from site_api.db.database import Database
from site_api.services.feed_import import FeedImportService
from site_api.services.feed_sources.csv_feed_source import CsvFeedSource, CsvFeedSourceError

# Feed category label -> our catalog_categories.slug. Extend this (or pass a
# retailer-specific map) as real feeds turn up category labels we don't recognize
# yet -- an unmapped label is skipped, not guessed at.
CATEGORY_HINT_MAP: dict[str, str] = {
    "Upper Receiver": "upper-receiver",
    "Upper Receivers": "upper-receiver",
    "Barrel": "barrel",
    "Barrels": "barrel",
    "Gas Block & Tube": "gas-system",
    "Gas Blocks": "gas-system",
    "Gas Tubes": "gas-system",
    "Handguard": "handguard",
    "Handguards": "handguard",
    "Bolt Carrier Group": "bolt-carrier-group",
    "Bolt Carrier Groups": "bolt-carrier-group",
    "BCGs": "bolt-carrier-group",
    "Charging Handle": "charging-handle",
    "Charging Handles": "charging-handle",
    "Lower Receiver": "lower-receiver",
    "Lower Receivers": "lower-receiver",
    "Trigger": "trigger",
    "Triggers": "trigger",
    "Pistol Grip": "pistol-grip",
    "Pistol Grips": "pistol-grip",
    "Magazine": "magazine",
    "Magazines": "magazine",
    "Stock & Brace": "stock-brace",
    "Stocks": "stock-brace",
    "Braces": "stock-brace",
    "Buffer Tubes": "stock-brace",
    "Optic": "optic",
    "Optics": "optic",
    "Red Dot Sights": "optic",
    "Scopes": "optic",
    "Optic Mounts": "optic",
    "Muzzle Device": "muzzle-device",
    "Muzzle Devices": "muzzle-device",
    "Muzzle Brakes": "muzzle-device",
    "Flash Hiders": "muzzle-device",
    "Compensators": "muzzle-device",
}


async def main(csv_path: Path, retailer: str) -> None:
    settings = Settings()
    database = Database(settings.database_url)

    print(f"Reading {csv_path}...")
    try:
        items = await CsvFeedSource(csv_path).fetch_items()
    except CsvFeedSourceError as error:
        print(f"Could not read feed: {error}")
        raise SystemExit(1) from None
    print(f"  {len(items)} item(s) parsed")

    async with database.session() as session:
        result = await FeedImportService(session, CATEGORY_HINT_MAP).import_items(retailer, items)

    print(f"\n{retailer}: {result.created} created, {result.updated} updated")
    if result.skipped_unmapped_category:
        print(f"Skipped {len(result.skipped_unmapped_category)} item(s) with an unmapped category:")
        for entry in result.skipped_unmapped_category[:20]:
            print(f"  - {entry}")
        if len(result.skipped_unmapped_category) > 20:
            print(f"  ...and {len(result.skipped_unmapped_category) - 20} more")

    await database.dispose()
    print("\nDone.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: uv run python {sys.argv[0]} <csv_path> <retailer_name>")
        raise SystemExit(1)

    _csv_path = Path(sys.argv[1])
    if not _csv_path.exists():
        print(f"No such file: {_csv_path}")
        raise SystemExit(1)

    asyncio.run(main(_csv_path, sys.argv[2]))
