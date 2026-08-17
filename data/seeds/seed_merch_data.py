"""Seed the merch store: hoodies and t-shirts with size variants.

All pricing, descriptions, and mockup imagery here are original placeholder
content for this project. Product images are flat illustrations generated
for this template, not real product photography.

Local development only. Run from backend/ with:
    uv run python ../data/seeds/seed_merch_data.py
"""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend" / "src"))

from sqlalchemy import select

from site_api.core.config import Settings
from site_api.core.slugify import slugify
from site_api.db.database import Database
from site_api.db.models import ItemVariantRecord, MarketplaceItemRecord, UserRecord

SIZES = ["S", "M", "L", "XL", "XXL"]

# (name, description, price_cents, image_url, out_of_stock_sizes)
ITEMS: list[tuple[str, str, int, str, list[str]]] = [
    (
        "Forge Logo T-Shirt — Black",
        "Soft cotton tee with the GunPartSelector.com mark printed on the chest.",
        2500,
        "/assets/images/merch/tshirt-black.svg",
        [],
    ),
    (
        "Forge Logo T-Shirt — Navy",
        "Soft cotton tee with the GunPartSelector.com mark printed on the chest.",
        2500,
        "/assets/images/merch/tshirt-navy.svg",
        [],
    ),
    (
        "Forge Logo T-Shirt — Red",
        "Soft cotton tee with the GunPartSelector.com mark printed on the chest.",
        2500,
        "/assets/images/merch/tshirt-red.svg",
        ["XXL"],
    ),
    (
        "Forge Pullover Hoodie — Black",
        "Heavyweight fleece pullover hoodie with a front pocket and the GunPartSelector.com mark on the chest.",
        4500,
        "/assets/images/merch/hoodie-black.svg",
        [],
    ),
    (
        "Forge Pullover Hoodie — Navy",
        "Heavyweight fleece pullover hoodie with a front pocket and the GunPartSelector.com mark on the chest.",
        4500,
        "/assets/images/merch/hoodie-navy.svg",
        ["S"],
    ),
    (
        "Forge Pullover Hoodie — Red",
        "Heavyweight fleece pullover hoodie with a front pocket and the GunPartSelector.com mark on the chest.",
        4500,
        "/assets/images/merch/hoodie-red.svg",
        [],
    ),
]


async def main() -> None:
    settings = Settings()
    database = Database(settings.database_url)

    async with database.session() as session:
        admin_row = await session.execute(
            select(UserRecord).where(UserRecord.email_address == "admin@example.com")
        )
        admin = admin_row.scalar_one_or_none()
        if admin is None:
            print("No admin@example.com account found — skipping seed (create an admin first).")
            return

        print("Seeding merch items...")
        for name, description, price_cents, image_url, out_of_stock_sizes in ITEMS:
            slug = slugify(name)
            existing = await session.execute(
                select(MarketplaceItemRecord.id).where(MarketplaceItemRecord.slug == slug)
            )
            item_id = existing.scalar_one_or_none()
            if item_id is not None:
                print(f"  already exists: {name}")
                continue

            item_id = uuid4()
            session.add(
                MarketplaceItemRecord(
                    id=item_id,
                    name=name,
                    slug=slug,
                    description=description,
                    price_cents=price_cents,
                    image_url=image_url,
                    is_active=True,
                    created_by_admin_id=admin.id,
                )
            )
            await session.flush()
            for sort_order, size in enumerate(SIZES):
                session.add(
                    ItemVariantRecord(
                        id=uuid4(),
                        marketplace_item_id=item_id,
                        label=size,
                        sort_order=sort_order,
                        stock_status="out_of_stock" if size in out_of_stock_sizes else "in_stock",
                    )
                )
            print(f"  created: {name}")

        await session.flush()

    await database.dispose()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
