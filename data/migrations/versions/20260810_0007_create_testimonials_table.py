"""Create testimonials table and seed mock testimonials.

Revision ID: 20260810_0007
Revises: 20260809_0006
Create Date: 2026-08-10
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260810_0007"
down_revision: str | None = "20260809_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TESTIMONIALS_TABLE = sa.table(
    "testimonials",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("customer_id", postgresql.UUID(as_uuid=True)),
    sa.column("customer_name", sa.String),
    sa.column("rating", sa.Integer),
    sa.column("body", sa.Text),
    sa.column("status", sa.String),
    sa.column("created_at", sa.DateTime(timezone=True)),
    sa.column("updated_at", sa.DateTime(timezone=True)),
)

_MOCK_TESTIMONIALS = [
    (
        "Priya Anand",
        5,
        "WD Web Solutions rebuilt our site in three weeks and our contact form "
        "submissions doubled the following month. Communication was clear the "
        "whole way through.",
    ),
    (
        "Marcus Webb",
        5,
        "They took our clunky old site and turned it into something we're "
        "actually proud to send customers to. The scheduling feature alone "
        "saved us hours every week.",
    ),
    (
        "Dana Ferreira",
        4,
        "Solid work and a fair price. There was a small delay getting the "
        "final assets together, but the team was responsive and the end "
        "result was worth it.",
    ),
    (
        "Tyler Osei",
        5,
        "Best web team we've worked with. They explained every decision in "
        "plain English instead of burying us in jargon, and the site has "
        "been rock solid since launch.",
    ),
    (
        "Renee Castellano",
        5,
        "Our online store went live ahead of schedule and checkout has been "
        "flawless. Support tickets get answered same day, every time.",
    ),
    (
        "Jordan Kim",
        4,
        "Great design instincts and fast turnaround. Would have liked a bit "
        "more guidance on SEO, but overall a very smooth project.",
    ),
    (
        "Aaliyah Brooks",
        5,
        "From the first call to launch day, everything felt organized. Our "
        "booking page now handles what used to be three phone calls and an "
        "email chain.",
    ),
    (
        "Sam Whitfield",
        5,
        "They understood exactly what our small business needed instead of "
        "trying to upsell us on things we didn't. Highly recommend.",
    ),
]


def upgrade() -> None:
    op.create_table(
        "testimonials",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("customer_name", sa.String(length=200), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"], name="fk_testimonials_customer_id"),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name="ck_testimonials_rating_range"),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')", name="ck_testimonials_status"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("customer_id", name="uq_testimonials_customer_id"),
    )

    now = datetime.now(UTC)
    rows = [
        {
            "id": uuid.uuid4(),
            "customer_id": None,
            "customer_name": name,
            "rating": rating,
            "body": body,
            "status": "approved",
            "created_at": now - timedelta(days=index * 9),
            "updated_at": now - timedelta(days=index * 9),
        }
        for index, (name, rating, body) in enumerate(_MOCK_TESTIMONIALS)
    ]
    op.bulk_insert(_TESTIMONIALS_TABLE, rows)


def downgrade() -> None:
    op.drop_table("testimonials")
