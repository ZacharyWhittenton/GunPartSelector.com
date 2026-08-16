"""Create user account storage.

Revision ID: 20260808_0002
Revises: 20260804_0001
Create Date: 2026-08-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260808_0002"
down_revision: str | None = "20260804_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email_address", sa.String(length=254), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('admin', 'customer', 'guest')",
            name="ck_users_role",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email_address", name="uq_users_email_address"),
    )


def downgrade() -> None:
    op.drop_table("users")
