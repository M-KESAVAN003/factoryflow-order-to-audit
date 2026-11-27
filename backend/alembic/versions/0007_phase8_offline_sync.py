"""Phase 8: Offline PWA order synchronization metadata and idempotency key constraint.

Revision ID: 0007_phase8_offline_sync
Revises: 0006_phase6
Create Date: 2026-11-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007_phase8_offline_sync"
down_revision: Union[str, None] = "0006_phase6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sales_orders", sa.Column("idempotency_key", sa.String(length=128), nullable=True))
    op.add_column("sales_orders", sa.Column("local_order_id", sa.String(length=128), nullable=True))
    op.add_column(
        "sales_orders",
        sa.Column("is_offline_order", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "sales_orders",
        sa.Column("offline_created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "sales_orders",
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "sales_orders",
        sa.Column("price_review_required", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("sales_orders", sa.Column("price_conflict_notes", sa.Text(), nullable=True))

    op.create_index(
        op.f("ix_sales_orders_idempotency_key"),
        "sales_orders",
        ["idempotency_key"],
        unique=True,
    )
    op.create_index(
        op.f("ix_sales_orders_local_order_id"),
        "sales_orders",
        ["local_order_id"],
        unique=False,
    )

    op.add_column(
        "sales_order_items",
        sa.Column("submitted_unit_price", sa.Numeric(precision=14, scale=2), nullable=True),
    )


def downgrade() -> None:
    with op.batch_alter_table("sales_order_items") as batch_op:
        batch_op.drop_column("submitted_unit_price")

    op.drop_index(op.f("ix_sales_orders_local_order_id"), table_name="sales_orders")
    op.drop_index(op.f("ix_sales_orders_idempotency_key"), table_name="sales_orders")

    with op.batch_alter_table("sales_orders") as batch_op:
        batch_op.drop_column("price_conflict_notes")
        batch_op.drop_column("price_review_required")
        batch_op.drop_column("synced_at")
        batch_op.drop_column("offline_created_at")
        batch_op.drop_column("is_offline_order")
        batch_op.drop_column("local_order_id")
        batch_op.drop_column("idempotency_key")
