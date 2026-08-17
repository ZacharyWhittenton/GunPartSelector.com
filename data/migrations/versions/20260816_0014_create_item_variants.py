"""Create item_variants and snapshot the purchased variant on order_items.

Revision ID: 20260816_0014
Revises: 20260815_0013
Create Date: 2026-08-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260816_0014"
down_revision: str | None = "20260815_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "item_variants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("marketplace_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.String(length=40), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "stock_status", sa.String(length=20), nullable=False, server_default="in_stock"
        ),
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
        sa.ForeignKeyConstraint(
            ["marketplace_item_id"],
            ["marketplace_items.id"],
            name="fk_item_variants_marketplace_item_id",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "stock_status IN ('in_stock', 'out_of_stock')", name="ck_item_variants_stock_status"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "marketplace_item_id", "label", name="uq_item_variants_item_label"
        ),
    )
    op.create_index(
        "ix_item_variants_marketplace_item_id", "item_variants", ["marketplace_item_id"]
    )

    op.add_column("order_items", sa.Column("variant_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column(
        "order_items",
        sa.Column("variant_label", sa.String(length=40), nullable=False, server_default=""),
    )
    op.create_foreign_key(
        "fk_order_items_variant_id",
        "order_items",
        "item_variants",
        ["variant_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_order_items_variant_id", "order_items", type_="foreignkey")
    op.drop_column("order_items", "variant_label")
    op.drop_column("order_items", "variant_id")
    op.drop_index("ix_item_variants_marketplace_item_id", table_name="item_variants")
    op.drop_table("item_variants")
