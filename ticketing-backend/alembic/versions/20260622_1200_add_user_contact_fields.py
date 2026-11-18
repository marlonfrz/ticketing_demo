"""add user contact fields

Revision ID: 20260622_1200
Revises: 20260611_1015
Create Date: 2026-06-22 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260622_1200"
down_revision: Union[str, None] = "20260611_1015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("phone", sa.String(length=50), nullable=True))
    op.add_column("users", sa.Column("country_code", sa.String(length=5), nullable=True))
    op.create_index(op.f("ix_users_phone"), "users", ["phone"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_phone"), table_name="users")
    op.drop_column("users", "country_code")
    op.drop_column("users", "phone")
