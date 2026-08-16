"""Create page_views and click_events tables for visitor analytics.

Revision ID: 20260810_0012
Revises: 20260810_0011
Create Date: 2026-08-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260810_0012"
down_revision: str | None = "20260810_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "page_views",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("path", sa.String(length=500), nullable=False),
        sa.Column("referrer", sa.String(length=500), nullable=True),
        sa.Column("session_id", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_page_views_path_created_at", "page_views", ["path", "created_at"])

    op.create_table(
        "click_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("path", sa.String(length=500), nullable=False),
        sa.Column("x_percent", sa.Float(), nullable=False),
        sa.Column("y_percent", sa.Float(), nullable=False),
        sa.Column("element_label", sa.String(length=200), nullable=True),
        sa.Column("session_id", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "x_percent >= 0 AND x_percent <= 100", name="ck_click_events_x_percent_range"
        ),
        sa.CheckConstraint(
            "y_percent >= 0 AND y_percent <= 100", name="ck_click_events_y_percent_range"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_click_events_path_created_at", "click_events", ["path", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_click_events_path_created_at", table_name="click_events")
    op.drop_table("click_events")
    op.drop_index("ix_page_views_path_created_at", table_name="page_views")
    op.drop_table("page_views")
