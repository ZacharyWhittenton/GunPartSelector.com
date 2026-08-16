"""Create lead_notes table for logging follow-up notes on leads.

Revision ID: 20260810_0009
Revises: 20260810_0008
Create Date: 2026-08-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260810_0009"
down_revision: str | None = "20260810_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lead_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_name", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["lead_id"], ["contact_requests.id"], name="fk_lead_notes_lead_id"
        ),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], name="fk_lead_notes_author_id"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lead_notes_lead_id", "lead_notes", ["lead_id"])


def downgrade() -> None:
    op.drop_index("ix_lead_notes_lead_id", table_name="lead_notes")
    op.drop_table("lead_notes")
