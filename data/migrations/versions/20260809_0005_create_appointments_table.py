"""Create appointments table for the scheduler feature.

Revision ID: 20260809_0005
Revises: 20260809_0004
Create Date: 2026-08-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260809_0005"
down_revision: str | None = "20260809_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "appointments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("client_name", sa.String(length=200), nullable=True),
        sa.Column("client_email", sa.String(length=254), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
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
            ["client_id"], ["users.id"], name="fk_appointments_client_id"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_admin_id"],
            ["users.id"],
            name="fk_appointments_created_by_admin_id",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'booked', 'cancelled')",
            name="ck_appointments_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_appointments_starts_at", "appointments", ["starts_at"])
    op.create_index("ix_appointments_client_id", "appointments", ["client_id"])


def downgrade() -> None:
    op.drop_index("ix_appointments_client_id", table_name="appointments")
    op.drop_index("ix_appointments_starts_at", table_name="appointments")
    op.drop_table("appointments")
