"""Add a follow-up reminder date to leads.

Revision ID: 20260810_0010
Revises: 20260810_0009
Create Date: 2026-08-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260810_0010"
down_revision: str | None = "20260810_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "contact_requests",
        sa.Column("follow_up_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("contact_requests", "follow_up_at")
