"""add guest checkout expiry

Revision ID: 20260805_0900
Revises: 20260716_0900
Create Date: 2026-08-05 09:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260805_0900"
down_revision: Union[str, None] = "20260716_0900"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "order_customers",
        sa.Column("guest_access_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        "UPDATE order_customers "
        "SET guest_access_expires_at = created_at + INTERVAL '24 hours'"
    )
    op.alter_column("order_customers", "guest_access_expires_at", nullable=False)


def downgrade() -> None:
    op.drop_column("order_customers", "guest_access_expires_at")
