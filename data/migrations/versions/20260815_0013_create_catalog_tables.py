"""Create catalog categories, products, builds, and build items.

Revision ID: 20260815_0013
Revises: 20260810_0012
Create Date: 2026-08-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260815_0013"
down_revision: str | None = "20260810_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "catalog_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(length=60), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("section", sa.String(length=30), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "section IN ('upper', 'lower', 'stock', 'optics', 'accessories')",
            name="ck_catalog_categories_section",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_catalog_categories_slug"),
    )

    op.create_table(
        "catalog_products",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("brand", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=220), nullable=False),
        sa.Column("sku", sa.String(length=100), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("price_cents", sa.Integer(), nullable=False),
        sa.Column("weight_oz", sa.Float(), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("affiliate_url", sa.String(length=500), nullable=False),
        sa.Column("affiliate_retailer_name", sa.String(length=100), nullable=True),
        sa.Column("stock_status", sa.String(length=20), nullable=False, server_default="in_stock"),
        sa.Column(
            "attribute_tags",
            postgresql.ARRAY(sa.String(length=60)),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
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
            ["category_id"], ["catalog_categories.id"], name="fk_catalog_products_category_id"
        ),
        sa.CheckConstraint("price_cents >= 0", name="ck_catalog_products_price_non_negative"),
        sa.CheckConstraint("weight_oz >= 0", name="ck_catalog_products_weight_non_negative"),
        sa.CheckConstraint(
            "stock_status IN ('in_stock', 'out_of_stock', 'unknown')",
            name="ck_catalog_products_stock_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_catalog_products_slug"),
    )
    op.create_index("ix_catalog_products_category_id", "catalog_products", ["category_id"])
    op.create_index("ix_catalog_products_brand", "catalog_products", ["brand"])

    op.create_table(
        "catalog_builds",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_catalog_builds_slug"),
    )

    op.create_table(
        "catalog_build_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("build_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(
            ["build_id"], ["catalog_builds.id"], name="fk_catalog_build_items_build_id"
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["catalog_products.id"], name="fk_catalog_build_items_product_id"
        ),
        sa.CheckConstraint("quantity > 0", name="ck_catalog_build_items_quantity_positive"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_catalog_build_items_build_id", "catalog_build_items", ["build_id"])
    op.create_index("ix_catalog_build_items_product_id", "catalog_build_items", ["product_id"])


def downgrade() -> None:
    op.drop_index("ix_catalog_build_items_product_id", table_name="catalog_build_items")
    op.drop_index("ix_catalog_build_items_build_id", table_name="catalog_build_items")
    op.drop_table("catalog_build_items")
    op.drop_table("catalog_builds")
    op.drop_index("ix_catalog_products_brand", table_name="catalog_products")
    op.drop_index("ix_catalog_products_category_id", table_name="catalog_products")
    op.drop_table("catalog_products")
    op.drop_table("catalog_categories")
