"""Add account status/last login to users and create account notes storage.

Revision ID: 20260808_0003
Revises: 20260808_0002
Create Date: 2026-08-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260808_0003"
down_revision: str | None = "20260808_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
    )
    op.add_column(
        "users",
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_users_status",
        "users",
        "status IN ('active', 'suspended')",
    )

    op.create_table(
        "account_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_name", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_account_notes_user_id"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], name="fk_account_notes_author_id"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_account_notes_user_id",
        "account_notes",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_account_notes_user_id", table_name="account_notes")
    op.drop_table("account_notes")
    op.drop_constraint("ck_users_status", "users", type_="check")
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "status")
