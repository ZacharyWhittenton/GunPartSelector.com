"""Add a lead pipeline to contact requests: more statuses + updated_at.

Revision ID: 20260810_0008
Revises: 20260810_0007
Create Date: 2026-08-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260810_0008"
down_revision: str | None = "20260810_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_STATUSES = "status IN ('received')"
_NEW_STATUSES = "status IN ('received', 'contacted', 'qualified', 'won', 'lost')"


def upgrade() -> None:
    op.add_column(
        "contact_requests",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=True,
        ),
    )
    op.execute("UPDATE contact_requests SET updated_at = created_at WHERE updated_at IS NULL")
    op.alter_column("contact_requests", "updated_at", nullable=False)

    op.drop_constraint("ck_contact_requests_status", "contact_requests", type_="check")
    op.create_check_constraint("ck_contact_requests_status", "contact_requests", _NEW_STATUSES)


def downgrade() -> None:
    op.drop_constraint("ck_contact_requests_status", "contact_requests", type_="check")
    op.create_check_constraint("ck_contact_requests_status", "contact_requests", _OLD_STATUSES)
    op.drop_column("contact_requests", "updated_at")
