"""add user consents

Revision ID: 20260622_1500
Revises: 20260622_1200
Create Date: 2026-06-22 15:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260622_1500"
down_revision: Union[str, None] = "20260622_1200"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("accepted_terms_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("accepted_privacy_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "marketing_consent",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column("marketing_consent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("marketing_consent_source", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "marketing_consent_source")
    op.drop_column("users", "marketing_consent_at")
    op.drop_column("users", "marketing_consent")
    op.drop_column("users", "accepted_privacy_at")
    op.drop_column("users", "accepted_terms_at")
