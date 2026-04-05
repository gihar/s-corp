"""Initial schema: users, meetings, user_events

Revision ID: 0001
Revises:
Create Date: 2026-04-05

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("full_name", sa.String(length=256), nullable=False),
        sa.Column("language_code", sa.String(length=10), nullable=True),
        sa.Column("is_subscribed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("subscription_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("protocols_used_this_month", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("protocols_month", sa.String(length=7), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "meetings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=True),
        sa.Column("participants", sa.Text(), nullable=True),
        sa.Column("agenda", sa.Text(), nullable=True),
        sa.Column("raw_notes", sa.Text(), nullable=True),
        sa.Column("protocol", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_meetings_user_id", "meetings", ["user_id"])

    op.create_table(
        "user_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("event", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_events_created_at", "user_events", ["created_at"])
    op.create_index("ix_user_events_event_at", "user_events", ["event", "created_at"])
    op.create_index("ix_user_events_user_id", "user_events", ["user_id"])


def downgrade() -> None:
    op.drop_table("user_events")
    op.drop_table("meetings")
    op.drop_table("users")
