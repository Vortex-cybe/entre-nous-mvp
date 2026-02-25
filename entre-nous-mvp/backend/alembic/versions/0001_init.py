"""init

Revision ID: 0001_init
Revises:
Create Date: 2026-02-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("password_hash", sa.String(length=256), nullable=False),
        sa.Column("email_lookup_hmac", sa.String(length=64), nullable=False),
        sa.Column("email_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("email_nonce", sa.LargeBinary(), nullable=False),
        sa.Column("trust_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("is_banned", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_created_at", "users", ["created_at"])
    op.create_index("ux_users_email_lookup_hmac", "users", ["email_lookup_hmac"], unique=True)

    op.create_table(
        "ip_bans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ip_lookup_hmac", sa.String(length=64), nullable=False, unique=True),
        sa.Column("ip_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("ip_nonce", sa.LargeBinary(), nullable=False),
        sa.Column("reason", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "posts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("body_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("body_nonce", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="visible"),
        sa.Column("toxicity_score", sa.Float(), nullable=True),
        sa.Column("flags_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_posts_created_at", "posts", ["created_at"])
    op.create_index("ix_posts_author_id", "posts", ["author_id"])

    op.create_table(
        "replies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("body_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("body_nonce", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="visible"),
        sa.Column("toxicity_score", sa.Float(), nullable=True),
        sa.Column("flags_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("kindness_votes", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_replies_post_id", "replies", ["post_id"])
    op.create_index("ix_replies_created_at", "replies", ["created_at"])

    op.create_table(
        "moderation_flags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("reporter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("target_type", sa.String(length=16), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.String(length=64), nullable=False),
        sa.Column("details", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_flags_target", "moderation_flags", ["target_type", "target_id"])

    op.create_table(
        "moderation_queue",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("target_type", sa.String(length=16), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_queue_status_priority", "moderation_queue", ["status", "priority", "created_at"])


def downgrade() -> None:
    op.drop_table("moderation_queue")
    op.drop_table("moderation_flags")
    op.drop_table("replies")
    op.drop_table("posts")
    op.drop_table("ip_bans")
    op.drop_index("ux_users_email_lookup_hmac", table_name="users")
    op.drop_index("ix_users_created_at", table_name="users")
    op.drop_table("users")
