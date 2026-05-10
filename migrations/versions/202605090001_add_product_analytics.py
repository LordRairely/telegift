"""add product analytics

Revision ID: 202605090001
Revises: 202604300001
Create Date: 2026-05-09 00:00:00.000000

"""
from collections.abc import Sequence
from typing import Optional, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202605090001"
down_revision: Optional[str] = "202604300001"
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None


def upgrade() -> None:
    op.add_column(
        "telegram_users",
        sa.Column("acquisition_source", sa.String(length=64), server_default="organic", nullable=False),
    )
    op.add_column("telegram_users", sa.Column("referral_code", sa.String(length=64), nullable=True))
    op.add_column("telegram_users", sa.Column("referred_by_code", sa.String(length=64), nullable=True))
    op.add_column(
        "telegram_users",
        sa.Column("analysis_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.add_column("telegram_users", sa.Column("last_analysis_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "telegram_users",
        sa.Column("has_paid", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.create_unique_constraint("uq_telegram_users_referral_code", "telegram_users", ["referral_code"])

    op.create_table(
        "gift_analyses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_user_id", sa.Integer(), nullable=False),
        sa.Column("file_format", sa.String(length=16), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="processing", nullable=False),
        sa.Column("error_type", sa.String(length=128), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["telegram_user_id"], ["telegram_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_gift_analyses_telegram_user_id", "gift_analyses", ["telegram_user_id"])

    op.create_table(
        "gift_feedback",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("analysis_id", sa.Integer(), nullable=False),
        sa.Column("gift_index", sa.Integer(), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["gift_analyses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_gift_feedback_analysis_id", "gift_feedback", ["analysis_id"])


def downgrade() -> None:
    op.drop_index("ix_gift_feedback_analysis_id", table_name="gift_feedback")
    op.drop_table("gift_feedback")
    op.drop_index("ix_gift_analyses_telegram_user_id", table_name="gift_analyses")
    op.drop_table("gift_analyses")
    op.drop_constraint("uq_telegram_users_referral_code", "telegram_users", type_="unique")
    op.drop_column("telegram_users", "has_paid")
    op.drop_column("telegram_users", "last_analysis_at")
    op.drop_column("telegram_users", "analysis_count")
    op.drop_column("telegram_users", "referred_by_code")
    op.drop_column("telegram_users", "referral_code")
    op.drop_column("telegram_users", "acquisition_source")
