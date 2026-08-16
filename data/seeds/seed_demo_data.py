"""Seed local dev data: mock accounts, account notes, blog posts, and open slots.

Local development only. Run from backend/ with:
    uv run python ../data/seeds/seed_demo_data.py
"""

import asyncio
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend" / "src"))

from site_api.core.config import Settings
from site_api.db.database import Database
from site_api.db.repositories import (
    SqlAlchemyAccountNoteRepository,
    SqlAlchemyAppointmentRepository,
    SqlAlchemyBlogPostRepository,
    SqlAlchemyCommentRepository,
    SqlAlchemyTagSubscriptionRepository,
    SqlAlchemyUserRepository,
)
from site_api.domain.users import EmailAlreadyRegisteredError, UserRole
from site_api.services.admin import AddAccountNote, AdminService
from site_api.services.auth import AuthService, RegisterUser
from site_api.services.blog import BlogService, CreatePost
from site_api.services.scheduling import BookSlot, CreateSlot, SchedulingService

MOCK_ACCOUNTS = [
    {
        "email_address": "morgan.rivera@example.com",
        "full_name": "Morgan Rivera",
        "password": "DemoPass123!",
        "notes": [
            "Filled out the contact form asking about a full website redesign. "
            "First-time visitor, hasn't booked a call yet.",
        ],
    },
    {
        "email_address": "jordan.blake@example.com",
        "full_name": "Jordan Blake",
        "password": "DemoPass123!",
        "notes": [
            "Existing client — launched their e-commerce storefront in June.",
            "Requested a quote for adding a customer loyalty program to their store.",
        ],
    },
    {
        "email_address": "casey.nguyen@example.com",
        "full_name": "Casey Nguyen",
        "password": "DemoPass123!",
        "notes": [
            "Referred by Jordan Blake. Interested in a custom web app for internal "
            "scheduling — sent over a rough spec doc.",
        ],
    },
    {
        "email_address": "priya.patel@example.com",
        "full_name": "Priya Patel",
        "password": "DemoPass123!",
        "notes": [
            "On our maintenance & support plan. Site check-in scheduled monthly.",
        ],
    },
    {
        "email_address": "sam.oconnor@example.com",
        "full_name": "Sam O'Connor",
        "password": "DemoPass123!",
        "notes": [],
    },
]

BLOG_POSTS = [
    {
        "title": "Carbine vs. Mid-Length vs. Rifle Gas Systems",
        "excerpt": "The gas system length behind your barrel changes recoil impulse, reliability, and which handguards will fit.",
        "body": (
            "Gas system length is set by where the gas port sits on the barrel, and it has "
            "a real effect on how a rifle shoots. Carbine-length systems are compact and "
            "common on shorter barrels but run a snappier recoil impulse. Mid-length "
            "systems soften that impulse and have become the default on 14.5-16 inch "
            "barrels. Rifle-length systems, originally spec'd for 20 inch barrels, give "
            "the softest cycling of the three. Whichever you pick, your handguard has to "
            "be long enough to clear the gas block — that's one of the checks our builder "
            "flags automatically."
        ),
        "tags": ("compatibility", "guides"),
    },
    {
        "title": "Mil-Spec vs. Commercial Buffer Tubes: Why It Matters",
        "excerpt": "Two buffer tube diameters exist, they aren't interchangeable, and the wrong stock won't fit.",
        "body": (
            "Mil-spec and commercial buffer tubes differ by about a tenth of an inch in "
            "outer diameter — small enough to miss, big enough that a commercial stock "
            "will not fit a mil-spec tube and vice versa. Mil-spec is the more common "
            "standard today and tends to have a wider aftermarket stock selection. Before "
            "you buy a stock or brace, confirm which spec your buffer tube (or complete "
            "lower) uses — it's one of the compatibility checks built into every "
            "GunPartSelector.com build."
        ),
        "tags": ("compatibility", "guides"),
    },
    {
        "title": "5.56 NATO, .223 Wylde, or .300 Blackout: Picking a Barrel",
        "excerpt": "Chamber choice affects what ammunition is safe to run and what your bolt carrier group needs to match.",
        "body": (
            "5.56 NATO chambers handle both 5.56 and .223 Remington safely; .223 Wylde "
            "chambers are cut for tighter accuracy while still safely running 5.56; and "
            ".300 Blackout is a different cartridge entirely, built around standard AR-15 "
            "magazines and bolt geometry but requiring a barrel, and often a bolt carrier "
            "group, chambered specifically for it. Whatever you land on, your barrel and "
            "BCG both need to agree on caliber — that mismatch is the single most common "
            "compatibility error we see."
        ),
        "tags": ("compatibility", "guides"),
    },
]


async def main() -> None:
    settings = Settings()
    database = Database(settings.database_url)

    async with database.session() as session:
        user_repository = SqlAlchemyUserRepository(session)
        note_repository = SqlAlchemyAccountNoteRepository(session)
        post_repository = SqlAlchemyBlogPostRepository(session)
        comment_repository = SqlAlchemyCommentRepository(session)
        tag_repository = SqlAlchemyTagSubscriptionRepository(session)
        appointment_repository = SqlAlchemyAppointmentRepository(session)

        auth_service = AuthService(user_repository)
        blog_service = BlogService(post_repository, comment_repository, tag_repository)
        scheduling_service = SchedulingService(appointment_repository)

        admin = await user_repository.get_by_email("admin@example.com")
        if admin is None:
            print("No admin@example.com account found — skipping seed (create an admin first).")
            return

        admin_service = AdminService(user_repository, note_repository)

        print("Seeding mock client/visitor accounts...")
        created_users = {}
        for account in MOCK_ACCOUNTS:
            try:
                user = await auth_service.register(
                    RegisterUser(
                        email_address=account["email_address"],
                        full_name=account["full_name"],
                        password=account["password"],
                    )
                )
                print(f"  created {user.full_name} <{user.email_address}>")
            except EmailAlreadyRegisteredError:
                user = await user_repository.get_by_email(account["email_address"])
                print(f"  already exists: {account['full_name']}")

            created_users[account["email_address"]] = user

            for note_body in account["notes"]:
                await admin_service.add_note(
                    AddAccountNote(
                        user_id=user.id,
                        author_id=admin.id,
                        author_name=admin.full_name,
                        body=note_body,
                    )
                )
            if account["notes"]:
                print(f"    added {len(account['notes'])} note(s)")

        print("\nSeeding blog posts...")
        for post_data in BLOG_POSTS:
            existing_posts = await post_repository.list_all()
            if any(p.title == post_data["title"] for p in existing_posts):
                print(f"  already exists: {post_data['title']}")
                continue

            post = await blog_service.create_post(
                CreatePost(
                    title=post_data["title"],
                    excerpt=post_data["excerpt"],
                    body=post_data["body"],
                    tags=post_data["tags"],
                    cover_image_url=None,
                    author_id=admin.id,
                    author_name=admin.full_name,
                )
            )
            await blog_service.publish_post(post.id)
            print(f"  created & published: {post.title}")

        print("\nSeeding open appointment slots...")
        now = datetime.now(UTC)
        base = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
        slot_offsets = [
            (0, 9), (0, 13), (1, 10), (2, 9), (2, 14), (3, 11),
        ]

        created_slots = []
        for day_offset, hour in slot_offsets:
            starts_at = base.replace(hour=hour) + timedelta(days=day_offset)
            slot = await scheduling_service.create_slot(
                CreateSlot(
                    starts_at=starts_at,
                    ends_at=starts_at + timedelta(minutes=30),
                    created_by_admin_id=admin.id,
                )
            )
            created_slots.append(slot)
            print(f"  open slot: {starts_at:%A %b %-d, %-I:%M %p}")

        client = created_users["jordan.blake@example.com"]
        booked = await scheduling_service.book_slot(
            BookSlot(
                slot_id=created_slots[0].id,
                client_id=client.id,
                client_name=client.full_name,
                client_email=client.email_address,
                notes="Wants to discuss adding a loyalty program to the storefront.",
            )
        )
        print(f"  booked slot for {client.full_name}: {booked.starts_at:%A %b %-d, %-I:%M %p}")

    await database.dispose()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
