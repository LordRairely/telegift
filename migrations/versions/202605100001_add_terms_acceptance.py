"""add terms acceptance

Revision ID: 202605100001
Revises: 202605090001
Create Date: 2026-05-10 00:00:00.000000

"""
from collections.abc import Sequence
from typing import Optional, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202605100001"
down_revision: Optional[str] = "202605090001"
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None


def upgrade() -> None:
    op.add_column("telegram_users", sa.Column("terms_accepted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("telegram_users", "terms_accepted_at")
