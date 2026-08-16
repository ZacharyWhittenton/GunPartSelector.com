"""Create discount codes and add discount tracking to orders.

Revision ID: 20260810_0011
Revises: 20260810_0010
Create Date: 2026-08-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260810_0011"
down_revision: str | None = "20260810_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "discount_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("discount_type", sa.String(length=10), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_redemptions", sa.Integer(), nullable=True),
        sa.Column("redemption_count", sa.Integer(), nullable=False, server_default="0"),
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
        sa.CheckConstraint("discount_type IN ('percent', 'fixed')", name="ck_discount_codes_type"),
        sa.CheckConstraint("value > 0", name="ck_discount_codes_value_positive"),
        sa.CheckConstraint(
            "discount_type != 'percent' OR value <= 100", name="ck_discount_codes_percent_max"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_discount_codes_code"),
    )

    op.add_column("orders", sa.Column("discount_code", sa.String(length=40), nullable=True))
    op.add_column(
        "orders",
        sa.Column("discount_cents", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("orders", "discount_cents")
    op.drop_column("orders", "discount_code")
    op.drop_table("discount_codes")
