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
        "title": "5 Signs Your Website Needs a Redesign",
        "excerpt": "If your site is slow, hard to update, or looks dated on mobile, it might be time for a refresh.",
        "body": (
            "Your website is often the first impression a potential customer has of your "
            "business. Here are five signs it's time for a redesign: slow load times, a "
            "layout that doesn't work well on phones, an outdated visual style, content "
            "that's a pain to update, and low conversion rates on your key calls to action. "
            "A modern rebuild focused on speed, clarity, and mobile-first design can turn "
            "your website from a liability into your best salesperson."
        ),
        "tags": ("web design", "tips"),
    },
    {
        "title": "Why Website Maintenance Matters",
        "excerpt": "A website isn't a one-time project — regular maintenance keeps it fast, secure, and reliable.",
        "body": (
            "Launching a website is just the beginning. Software dependencies need "
            "updates, security patches need to be applied, and broken links or outdated "
            "content can quietly erode trust with visitors. A regular maintenance plan "
            "catches these issues before they become problems, keeps your site running "
            "fast, and gives you peace of mind that your online presence is in good hands."
        ),
        "tags": ("maintenance", "security"),
    },
    {
        "title": "Choosing the Right E-Commerce Platform for Your Business",
        "excerpt": "From inventory management to checkout flow, the right platform depends on how you sell.",
        "body": (
            "Not all e-commerce platforms are built the same. Before choosing one, think "
            "about your catalog size, whether you need custom checkout logic, how you "
            "manage inventory, and what integrations matter most — payment processors, "
            "shipping providers, or your existing business tools. We help clients weigh "
            "these tradeoffs and build a storefront that fits how they actually sell, "
            "not just a generic template."
        ),
        "tags": ("e-commerce", "business"),
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
