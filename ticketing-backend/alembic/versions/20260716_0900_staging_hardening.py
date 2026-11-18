"""staging hardening

Revision ID: 20260716_0900
Revises: 20260622_1500
Create Date: 2026-07-16 09:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260716_0900"
down_revision: Union[str, None] = "20260622_1500"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS validator_assignments")
    op.execute("DROP TABLE IF EXISTS promoter_validators")

    op.drop_index("ix_payments_order_id", table_name="payments")
    op.drop_index("ix_payments_provider_order_id", table_name="payments")
    op.drop_index("ix_payments_provider_payment_id", table_name="payments")
    op.create_index("ix_payments_order_id", "payments", ["order_id"], unique=True)
    op.create_index(
        "ix_payments_provider_order_id",
        "payments",
        ["provider_order_id"],
        unique=True,
    )
    op.create_index(
        "ix_payments_provider_payment_id",
        "payments",
        ["provider_payment_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_payments_provider_payment_id", table_name="payments")
    op.drop_index("ix_payments_provider_order_id", table_name="payments")
    op.drop_index("ix_payments_order_id", table_name="payments")
    op.create_index("ix_payments_provider_payment_id", "payments", ["provider_payment_id"])
    op.create_index("ix_payments_provider_order_id", "payments", ["provider_order_id"])
    op.create_index("ix_payments_order_id", "payments", ["order_id"])

    op.create_table(
        "promoter_validators",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("promoter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("validator_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("assigned_by_admin_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_promoter_validators_promoter_id", "promoter_validators", ["promoter_id"])
    op.create_index(
        "ix_promoter_validators_validator_user_id",
        "promoter_validators",
        ["validator_user_id"],
    )
    op.create_index(
        "ix_promoter_validators_assigned_by_admin_id",
        "promoter_validators",
        ["assigned_by_admin_id"],
    )

    op.create_table(
        "validator_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("validator_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("promoter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("events.id"), nullable=False),
        sa.Column("assigned_by_admin_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("active_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_validator_assignments_validator_user_id",
        "validator_assignments",
        ["validator_user_id"],
    )
    op.create_index("ix_validator_assignments_promoter_id", "validator_assignments", ["promoter_id"])
    op.create_index("ix_validator_assignments_event_id", "validator_assignments", ["event_id"])
    op.create_index(
        "ix_validator_assignments_assigned_by_admin_id",
        "validator_assignments",
        ["assigned_by_admin_id"],
    )
