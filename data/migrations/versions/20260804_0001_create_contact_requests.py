"""Create contact request storage.

Revision ID: 20260804_0001
Revises:
Create Date: 2026-08-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260804_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "contact_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("email_address", sa.String(length=254), nullable=False),
        sa.Column("company", sa.String(length=200), nullable=True),
        sa.Column("phone", sa.String(length=40), nullable=True),
        sa.Column("service", sa.String(length=200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('received')",
            name="ck_contact_requests_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_contact_requests_created_at",
        "contact_requests",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_contact_requests_created_at", table_name="contact_requests")
    op.drop_table("contact_requests")
