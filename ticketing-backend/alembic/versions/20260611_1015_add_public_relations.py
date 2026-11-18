"""add public relations tracking

Revision ID: 20260611_1015
Revises: c47ecd2ef962
Create Date: 2026-06-11 10:15:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260611_1015"
down_revision: Union[str, None] = "c47ecd2ef962"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "public_relations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("social_handle", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("sales_code", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("accepted_privacy_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "sales_code", name="uq_public_relations_event_sales_code"),
    )
    op.create_index(op.f("ix_public_relations_event_id"), "public_relations", ["event_id"], unique=False)
    op.create_index(op.f("ix_public_relations_sales_code"), "public_relations", ["sales_code"], unique=False)

    op.add_column("orders", sa.Column("public_relations_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f("ix_orders_public_relations_id"), "orders", ["public_relations_id"], unique=False)
    op.create_foreign_key(
        "fk_orders_public_relations_id_public_relations",
        "orders",
        "public_relations",
        ["public_relations_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_orders_public_relations_id_public_relations", "orders", type_="foreignkey")
    op.drop_index(op.f("ix_orders_public_relations_id"), table_name="orders")
    op.drop_column("orders", "public_relations_id")

    op.drop_index(op.f("ix_public_relations_sales_code"), table_name="public_relations")
    op.drop_index(op.f("ix_public_relations_event_id"), table_name="public_relations")
    op.drop_table("public_relations")
