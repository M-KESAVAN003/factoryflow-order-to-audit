"""Phase 3: inventory balances, append-only stock ledger, stock adjustments, and purchases.

Revision ID: 0003_phase3
Revises: 0002_phase2
Create Date: 2026-11-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_phase3"
down_revision: Union[str, None] = "0002_phase2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stock_balances",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("stock_item_id", sa.String(length=36), nullable=False),
        sa.Column("available_quantity", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("average_cost", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("total_value", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("last_movement_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["stock_item_id"], ["stock_items.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_stock_balances_stock_item_id"), "stock_balances", ["stock_item_id"], unique=True
    )

    op.create_table(
        "stock_ledger",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("stock_item_id", sa.String(length=36), nullable=False),
        sa.Column(
            "movement_type",
            sa.Enum(
                "OPENING_STOCK",
                "PURCHASE_RECEIPT",
                "PRODUCTION_ISSUE",
                "PRODUCTION_OUTPUT",
                "SALES_DISPATCH",
                "SALES_RETURN",
                "PURCHASE_RETURN",
                "STOCK_ADJUSTMENT",
                "REVERSAL",
                name="stock_movement_type_enum",
            ),
            nullable=False,
        ),
        sa.Column("quantity_in", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("quantity_out", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("base_unit_id", sa.String(length=36), nullable=False),
        sa.Column("reference_doc_type", sa.String(length=60), nullable=False),
        sa.Column("reference_doc_id", sa.String(length=80), nullable=False),
        sa.Column("transaction_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("unit_cost", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("total_value", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("balance_qty_after", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("avg_cost_after", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("balance_value_after", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["base_unit_id"], ["units.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["stock_item_id"], ["stock_items.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_stock_ledger_created_at"), "stock_ledger", ["created_at"], unique=False)
    op.create_index(op.f("ix_stock_ledger_movement_type"), "stock_ledger", ["movement_type"], unique=False)
    op.create_index(op.f("ix_stock_ledger_reference_doc_id"), "stock_ledger", ["reference_doc_id"], unique=False)
    op.create_index(op.f("ix_stock_ledger_reference_doc_type"), "stock_ledger", ["reference_doc_type"], unique=False)
    op.create_index(op.f("ix_stock_ledger_stock_item_id"), "stock_ledger", ["stock_item_id"], unique=False)
    op.create_index(op.f("ix_stock_ledger_transaction_date"), "stock_ledger", ["transaction_date"], unique=False)

    op.create_table(
        "stock_adjustments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("stock_item_id", sa.String(length=36), nullable=False),
        sa.Column("current_balance", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("physical_count", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("difference", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("reason", sa.String(length=200), nullable=False),
        sa.Column("supporting_notes", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("PENDING", "APPROVED", name="stock_adjustment_status_enum"),
            nullable=False,
        ),
        sa.Column("adjustment_date", sa.Date(), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("approved_by", sa.String(length=36), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["stock_item_id"], ["stock_items.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_stock_adjustments_status"), "stock_adjustments", ["status"], unique=False)
    op.create_index(op.f("ix_stock_adjustments_stock_item_id"), "stock_adjustments", ["stock_item_id"], unique=False)

    op.create_table(
        "purchases",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("reference_number", sa.String(length=64), nullable=False),
        sa.Column("supplier_id", sa.String(length=36), nullable=False),
        sa.Column("purchase_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("DRAFT", "REVIEWED", "POSTED", "CANCELLED", name="purchase_status_enum"),
            nullable=False,
        ),
        sa.Column(
            "payment_status",
            sa.Enum("UNPAID", "PARTIAL", "PAID", name="purchase_payment_status_enum"),
            nullable=False,
        ),
        sa.Column("subtotal", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("tax_amount", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("total_amount", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("reviewed_by", sa.String(length=36), nullable=True),
        sa.Column("posted_by", sa.String(length=36), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", sa.String(length=36), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["cancelled_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["posted_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_purchases_purchase_date"), "purchases", ["purchase_date"], unique=False)
    op.create_index(op.f("ix_purchases_reference_number"), "purchases", ["reference_number"], unique=True)
    op.create_index(op.f("ix_purchases_status"), "purchases", ["status"], unique=False)
    op.create_index(op.f("ix_purchases_supplier_id"), "purchases", ["supplier_id"], unique=False)

    op.create_table(
        "purchase_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("purchase_id", sa.String(length=36), nullable=False),
        sa.Column("stock_item_id", sa.String(length=36), nullable=False),
        sa.Column("unit_id", sa.String(length=36), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("base_quantity", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("unit_rate", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("tax_rate", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("tax_amount", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("line_subtotal", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("line_total", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.ForeignKeyConstraint(["purchase_id"], ["purchases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stock_item_id"], ["stock_items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_purchase_items_purchase_id"), "purchase_items", ["purchase_id"], unique=False)
    op.create_index(op.f("ix_purchase_items_stock_item_id"), "purchase_items", ["stock_item_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_purchase_items_stock_item_id"), table_name="purchase_items")
    op.drop_index(op.f("ix_purchase_items_purchase_id"), table_name="purchase_items")
    op.drop_table("purchase_items")

    op.drop_index(op.f("ix_purchases_supplier_id"), table_name="purchases")
    op.drop_index(op.f("ix_purchases_status"), table_name="purchases")
    op.drop_index(op.f("ix_purchases_reference_number"), table_name="purchases")
    op.drop_index(op.f("ix_purchases_purchase_date"), table_name="purchases")
    op.drop_table("purchases")

    op.drop_index(op.f("ix_stock_adjustments_stock_item_id"), table_name="stock_adjustments")
    op.drop_index(op.f("ix_stock_adjustments_status"), table_name="stock_adjustments")
    op.drop_table("stock_adjustments")

    op.drop_index(op.f("ix_stock_ledger_transaction_date"), table_name="stock_ledger")
    op.drop_index(op.f("ix_stock_ledger_stock_item_id"), table_name="stock_ledger")
    op.drop_index(op.f("ix_stock_ledger_reference_doc_type"), table_name="stock_ledger")
    op.drop_index(op.f("ix_stock_ledger_reference_doc_id"), table_name="stock_ledger")
    op.drop_index(op.f("ix_stock_ledger_movement_type"), table_name="stock_ledger")
    op.drop_index(op.f("ix_stock_ledger_created_at"), table_name="stock_ledger")
    op.drop_table("stock_ledger")

    op.drop_index(op.f("ix_stock_balances_stock_item_id"), table_name="stock_balances")
    op.drop_table("stock_balances")

    sa.Enum(name="purchase_payment_status_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="purchase_status_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="stock_adjustment_status_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="stock_movement_type_enum").drop(op.get_bind(), checkfirst=True)
