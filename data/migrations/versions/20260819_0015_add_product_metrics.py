"""Add view_count to catalog_products and index affiliate_retailer_name.

Revision ID: 20260819_0015
Revises: 20260816_0014
Create Date: 2026-08-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260819_0015"
down_revision: str | None = "20260816_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "catalog_products",
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index(
        "ix_catalog_products_affiliate_retailer_name",
        "catalog_products",
        ["affiliate_retailer_name"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_catalog_products_affiliate_retailer_name", table_name="catalog_products"
    )
    op.drop_column("catalog_products", "view_count")
