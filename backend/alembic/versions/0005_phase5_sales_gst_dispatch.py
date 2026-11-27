"""Phase 5: Sales orders, immutable GST invoices, credit notes, and finished-goods dispatches.

Revision ID: 0005_phase5
Revises: 0004_phase4
Create Date: 2026-11-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0005_phase5"
down_revision: Union[str, None] = "0004_phase4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _gst_tax_type_enum(bind, *, create_type: bool) -> sa.Enum:
    if bind.dialect.name == "postgresql":
        return postgresql.ENUM(
            "INTRA_STATE",
            "INTER_STATE",
            name="gst_tax_type_enum",
            create_type=create_type,
        )
    return sa.Enum("INTRA_STATE", "INTER_STATE", name="gst_tax_type_enum")


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        "sales_orders",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("order_number", sa.String(length=64), nullable=False),
        sa.Column("customer_id", sa.String(length=36), nullable=False),
        sa.Column("salesman_id", sa.String(length=36), nullable=False),
        sa.Column("order_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "SUBMITTED",
                "UNDER_REVIEW",
                "APPROVED",
                "AWAITING_STOCK",
                "PARTIALLY_FULFILLED",
                "INVOICED",
                "DISPATCHED",
                "REJECTED",
                "CANCELLED",
                name="sales_order_status_enum",
            ),
            nullable=False,
        ),
        sa.Column("factory_state", sa.String(length=80), nullable=False),
        sa.Column("customer_state", sa.String(length=80), nullable=False),
        sa.Column("place_of_supply", sa.String(length=80), nullable=False),
        sa.Column("tax_type", _gst_tax_type_enum(bind, create_type=True), nullable=False),
        sa.Column("subtotal", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("cgst_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("sgst_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("igst_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("tax_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("total_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("has_stock_shortage", sa.Boolean(), nullable=False),
        sa.Column("shortage_notes", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("reviewed_by", sa.String(length=36), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.String(length=36), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_by", sa.String(length=36), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["rejected_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["salesman_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sales_orders_created_at"), "sales_orders", ["created_at"], unique=False)
    op.create_index(op.f("ix_sales_orders_customer_id"), "sales_orders", ["customer_id"], unique=False)
    op.create_index(op.f("ix_sales_orders_order_date"), "sales_orders", ["order_date"], unique=False)
    op.create_index(op.f("ix_sales_orders_order_number"), "sales_orders", ["order_number"], unique=True)
    op.create_index(op.f("ix_sales_orders_salesman_id"), "sales_orders", ["salesman_id"], unique=False)
    op.create_index(op.f("ix_sales_orders_status"), "sales_orders", ["status"], unique=False)

    op.create_table(
        "sales_order_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("sales_order_id", sa.String(length=36), nullable=False),
        sa.Column("product_id", sa.String(length=36), nullable=False),
        sa.Column("stock_item_id", sa.String(length=36), nullable=False),
        sa.Column("unit_id", sa.String(length=36), nullable=False),
        sa.Column("hsn_code", sa.String(length=20), nullable=False),
        sa.Column("requested_quantity", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("approved_quantity", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("dispatched_quantity", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("gst_rate", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("taxable_value", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("cgst_rate", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("sgst_rate", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("igst_rate", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("cgst_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("sgst_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("igst_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("line_total", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["sales_order_id"], ["sales_orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stock_item_id"], ["stock_items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sales_order_items_product_id"), "sales_order_items", ["product_id"], unique=False)
    op.create_index(op.f("ix_sales_order_items_sales_order_id"), "sales_order_items", ["sales_order_id"], unique=False)
    op.create_index(op.f("ix_sales_order_items_stock_item_id"), "sales_order_items", ["stock_item_id"], unique=False)

    op.create_table(
        "invoices",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("invoice_number", sa.String(length=64), nullable=False),
        sa.Column("financial_year", sa.String(length=16), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("sales_order_id", sa.String(length=36), nullable=False),
        sa.Column("customer_id", sa.String(length=36), nullable=False),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("status", sa.Enum("POSTED", name="invoice_status_enum"), nullable=False),
        sa.Column("factory_name", sa.String(length=150), nullable=False),
        sa.Column("factory_address", sa.Text(), nullable=False),
        sa.Column("factory_gstin", sa.String(length=15), nullable=False),
        sa.Column("factory_state", sa.String(length=80), nullable=False),
        sa.Column("factory_state_code", sa.String(length=5), nullable=False),
        sa.Column("customer_name", sa.String(length=150), nullable=False),
        sa.Column("customer_gstin", sa.String(length=15), nullable=False),
        sa.Column("billing_address", sa.Text(), nullable=False),
        sa.Column("customer_state", sa.String(length=80), nullable=False),
        sa.Column("place_of_supply", sa.String(length=80), nullable=False),
        sa.Column("tax_type", _gst_tax_type_enum(bind, create_type=False), nullable=False),
        sa.Column("subtotal", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("cgst_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("sgst_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("igst_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("tax_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("grand_total", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("amount_in_words", sa.String(length=300), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["sales_order_id"], ["sales_orders.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("financial_year", "sequence_number", name="uq_invoice_fy_sequence"),
        sa.UniqueConstraint("sales_order_id", name="uq_invoice_sales_order"),
    )
    op.create_index(op.f("ix_invoices_created_at"), "invoices", ["created_at"], unique=False)
    op.create_index(op.f("ix_invoices_customer_id"), "invoices", ["customer_id"], unique=False)
    op.create_index(op.f("ix_invoices_financial_year"), "invoices", ["financial_year"], unique=False)
    op.create_index(op.f("ix_invoices_invoice_date"), "invoices", ["invoice_date"], unique=False)
    op.create_index(op.f("ix_invoices_invoice_number"), "invoices", ["invoice_number"], unique=True)
    op.create_index(op.f("ix_invoices_sales_order_id"), "invoices", ["sales_order_id"], unique=False)

    op.create_table(
        "invoice_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("invoice_id", sa.String(length=36), nullable=False),
        sa.Column("sales_order_item_id", sa.String(length=36), nullable=False),
        sa.Column("product_id", sa.String(length=36), nullable=False),
        sa.Column("product_name", sa.String(length=150), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("pack_size", sa.String(length=60), nullable=False),
        sa.Column("hsn_code", sa.String(length=20), nullable=False),
        sa.Column("unit_symbol", sa.String(length=20), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("gst_rate", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("taxable_value", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("cgst_rate", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("sgst_rate", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("igst_rate", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("cgst_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("sgst_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("igst_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("line_total", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["sales_order_item_id"], ["sales_order_items.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_invoice_items_invoice_id"), "invoice_items", ["invoice_id"], unique=False)

    op.create_table(
        "credit_notes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("credit_note_number", sa.String(length=64), nullable=False),
        sa.Column("invoice_id", sa.String(length=36), nullable=False),
        sa.Column("financial_year", sa.String(length=16), nullable=False),
        sa.Column("credit_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_credit_notes_credit_note_number"), "credit_notes", ["credit_note_number"], unique=True)
    op.create_index(op.f("ix_credit_notes_invoice_id"), "credit_notes", ["invoice_id"], unique=False)

    op.create_table(
        "dispatches",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("dispatch_number", sa.String(length=64), nullable=False),
        sa.Column("sales_order_id", sa.String(length=36), nullable=False),
        sa.Column("invoice_id", sa.String(length=36), nullable=False),
        sa.Column("dispatch_date", sa.Date(), nullable=False),
        sa.Column("vehicle_number", sa.String(length=64), nullable=True),
        sa.Column("transporter_name", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("dispatched_by", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["dispatched_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["sales_order_id"], ["sales_orders.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invoice_id", name="uq_dispatch_invoice"),
        sa.UniqueConstraint("sales_order_id", name="uq_dispatch_sales_order"),
    )
    op.create_index(op.f("ix_dispatches_created_at"), "dispatches", ["created_at"], unique=False)
    op.create_index(op.f("ix_dispatches_dispatch_date"), "dispatches", ["dispatch_date"], unique=False)
    op.create_index(op.f("ix_dispatches_dispatch_number"), "dispatches", ["dispatch_number"], unique=True)
    op.create_index(op.f("ix_dispatches_invoice_id"), "dispatches", ["invoice_id"], unique=False)
    op.create_index(op.f("ix_dispatches_sales_order_id"), "dispatches", ["sales_order_id"], unique=False)

    op.create_table(
        "dispatch_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("dispatch_id", sa.String(length=36), nullable=False),
        sa.Column("sales_order_item_id", sa.String(length=36), nullable=False),
        sa.Column("product_id", sa.String(length=36), nullable=False),
        sa.Column("stock_item_id", sa.String(length=36), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("stock_ledger_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["dispatch_id"], ["dispatches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["sales_order_item_id"], ["sales_order_items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["stock_item_id"], ["stock_items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["stock_ledger_id"], ["stock_ledger.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_dispatch_items_dispatch_id"), "dispatch_items", ["dispatch_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_dispatch_items_dispatch_id"), table_name="dispatch_items")
    op.drop_table("dispatch_items")

    op.drop_index(op.f("ix_dispatches_sales_order_id"), table_name="dispatches")
    op.drop_index(op.f("ix_dispatches_invoice_id"), table_name="dispatches")
    op.drop_index(op.f("ix_dispatches_dispatch_number"), table_name="dispatches")
    op.drop_index(op.f("ix_dispatches_dispatch_date"), table_name="dispatches")
    op.drop_index(op.f("ix_dispatches_created_at"), table_name="dispatches")
    op.drop_table("dispatches")

    op.drop_index(op.f("ix_credit_notes_invoice_id"), table_name="credit_notes")
    op.drop_index(op.f("ix_credit_notes_credit_note_number"), table_name="credit_notes")
    op.drop_table("credit_notes")

    op.drop_index(op.f("ix_invoice_items_invoice_id"), table_name="invoice_items")
    op.drop_table("invoice_items")

    op.drop_index(op.f("ix_invoices_sales_order_id"), table_name="invoices")
    op.drop_index(op.f("ix_invoices_invoice_number"), table_name="invoices")
    op.drop_index(op.f("ix_invoices_invoice_date"), table_name="invoices")
    op.drop_index(op.f("ix_invoices_financial_year"), table_name="invoices")
    op.drop_index(op.f("ix_invoices_customer_id"), table_name="invoices")
    op.drop_index(op.f("ix_invoices_created_at"), table_name="invoices")
    op.drop_table("invoices")

    op.drop_index(op.f("ix_sales_order_items_stock_item_id"), table_name="sales_order_items")
    op.drop_index(op.f("ix_sales_order_items_sales_order_id"), table_name="sales_order_items")
    op.drop_index(op.f("ix_sales_order_items_product_id"), table_name="sales_order_items")
    op.drop_table("sales_order_items")

    op.drop_index(op.f("ix_sales_orders_status"), table_name="sales_orders")
    op.drop_index(op.f("ix_sales_orders_salesman_id"), table_name="sales_orders")
    op.drop_index(op.f("ix_sales_orders_order_number"), table_name="sales_orders")
    op.drop_index(op.f("ix_sales_orders_order_date"), table_name="sales_orders")
    op.drop_index(op.f("ix_sales_orders_customer_id"), table_name="sales_orders")
    op.drop_index(op.f("ix_sales_orders_created_at"), table_name="sales_orders")
    op.drop_table("sales_orders")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        sa.Enum(name="invoice_status_enum").drop(bind, checkfirst=True)
        sa.Enum(name="sales_order_status_enum").drop(bind, checkfirst=True)
        sa.Enum(name="gst_tax_type_enum").drop(bind, checkfirst=True)
