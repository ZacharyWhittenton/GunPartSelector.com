"""Create blog posts, comments, and tag subscriptions storage.

Revision ID: 20260809_0004
Revises: 20260808_0003
Create Date: 2026-08-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260809_0004"
down_revision: str | None = "20260808_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "blog_posts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=220), nullable=False),
        sa.Column("excerpt", sa.String(length=500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("cover_image_url", sa.String(length=500), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String(length=60)), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_name", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], name="fk_blog_posts_author_id"),
        sa.CheckConstraint(
            "status IN ('draft', 'published')",
            name="ck_blog_posts_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_blog_posts_slug"),
    )

    op.create_table(
        "comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_name", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["post_id"], ["blog_posts.id"], name="fk_comments_post_id"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], name="fk_comments_author_id"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comments_post_id", "comments", ["post_id"])

    op.create_table(
        "tag_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tag_name", sa.String(length=60), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_tag_subscriptions_user_id"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "tag_name", name="uq_tag_subscriptions_user_tag"),
    )
    op.create_index("ix_tag_subscriptions_user_id", "tag_subscriptions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_tag_subscriptions_user_id", table_name="tag_subscriptions")
    op.drop_table("tag_subscriptions")
    op.drop_index("ix_comments_post_id", table_name="comments")
    op.drop_table("comments")
    op.drop_table("blog_posts")
