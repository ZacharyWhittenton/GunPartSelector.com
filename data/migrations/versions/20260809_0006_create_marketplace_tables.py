"""Create marketplace items, orders, order items, and wishlist storage.

Revision ID: 20260809_0006
Revises: 20260809_0005
Create Date: 2026-08-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260809_0006"
down_revision: str | None = "20260809_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "marketplace_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=220), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("price_cents", sa.Integer(), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_admin_id", postgresql.UUID(as_uuid=True), nullable=False),
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
            ["created_by_admin_id"], ["users.id"], name="fk_marketplace_items_created_by_admin_id"
        ),
        sa.CheckConstraint("price_cents >= 0", name="ck_marketplace_items_price_non_negative"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_marketplace_items_slug"),
    )

    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stripe_checkout_session_id", sa.String(length=255), nullable=False),
        sa.Column("stripe_payment_intent_id", sa.String(length=255), nullable=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("customer_email", sa.String(length=254), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("total_cents", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"], name="fk_orders_customer_id"),
        sa.CheckConstraint(
            "status IN ('open', 'paid', 'expired', 'cancelled')", name="ck_orders_status"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "stripe_checkout_session_id", name="uq_orders_stripe_checkout_session_id"
        ),
    )
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"])

    op.create_table(
        "order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("marketplace_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("item_name", sa.String(length=200), nullable=False),
        sa.Column("unit_price_cents", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("line_total_cents", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], name="fk_order_items_order_id"),
        sa.ForeignKeyConstraint(
            ["marketplace_item_id"],
            ["marketplace_items.id"],
            name="fk_order_items_marketplace_item_id",
        ),
        sa.CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])

    op.create_table(
        "wishlist_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("marketplace_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_wishlist_items_user_id"),
        sa.ForeignKeyConstraint(
            ["marketplace_item_id"],
            ["marketplace_items.id"],
            name="fk_wishlist_items_marketplace_item_id",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "marketplace_item_id", name="uq_wishlist_items_user_item"
        ),
    )
    op.create_index("ix_wishlist_items_user_id", "wishlist_items", ["user_id"])
    op.create_index(
        "ix_wishlist_items_marketplace_item_id", "wishlist_items", ["marketplace_item_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_wishlist_items_marketplace_item_id", table_name="wishlist_items")
    op.drop_index("ix_wishlist_items_user_id", table_name="wishlist_items")
    op.drop_table("wishlist_items")
    op.drop_index("ix_order_items_order_id", table_name="order_items")
    op.drop_table("order_items")
    op.drop_index("ix_orders_customer_id", table_name="orders")
    op.drop_table("orders")
    op.drop_table("marketplace_items")
