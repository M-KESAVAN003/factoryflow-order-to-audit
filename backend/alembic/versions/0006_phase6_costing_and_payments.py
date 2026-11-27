"""Phase 6: Production expenses, customer payments, and invoice payment allocations.

Revision ID: 0006_phase6
Revises: 0005_phase5
Create Date: 2026-11-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006_phase6"
down_revision: Union[str, None] = "0005_phase5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "production_expenses",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("expense_number", sa.String(length=64), nullable=False),
        sa.Column("production_run_id", sa.String(length=36), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "LABOUR",
                "GAS",
                "ELECTRICITY",
                "POWER",
                "MAINTENANCE",
                "OTHER_OVERHEAD",
                name="production_expense_category_enum",
            ),
            nullable=False,
        ),
        sa.Column("description", sa.String(length=250), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("DRAFT", "POSTED", "REVERSED", name="production_expense_status_enum"),
            nullable=False,
        ),
        sa.Column("reversal_of_id", sa.String(length=36), nullable=True),
        sa.Column("recorded_by", sa.String(length=36), nullable=False),
        sa.Column("posted_by", sa.String(length=36), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["posted_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["production_run_id"], ["production_runs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recorded_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reversal_of_id"], ["production_expenses.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_production_expenses_category"), "production_expenses", ["category"], unique=False)
    op.create_index(op.f("ix_production_expenses_expense_date"), "production_expenses", ["expense_date"], unique=False)
    op.create_index(op.f("ix_production_expenses_expense_number"), "production_expenses", ["expense_number"], unique=True)
    op.create_index(op.f("ix_production_expenses_production_run_id"), "production_expenses", ["production_run_id"], unique=False)
    op.create_index(op.f("ix_production_expenses_status"), "production_expenses", ["status"], unique=False)

    op.create_table(
        "payments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("payment_reference", sa.String(length=64), nullable=False),
        sa.Column("customer_id", sa.String(length=36), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column(
            "payment_method",
            sa.Enum("CASH", "BANK_TRANSFER", "UPI", "CHEQUE", "OTHER", name="customer_payment_method_enum"),
            nullable=False,
        ),
        sa.Column("amount_received", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("allocated_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("unallocated_advance", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("transaction_reference", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("DRAFT", "POSTED", "REVERSED", name="customer_payment_status_enum"),
            nullable=False,
        ),
        sa.Column("reversal_of_id", sa.String(length=36), nullable=True),
        sa.Column("recorded_by", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recorded_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reversal_of_id"], ["payments.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_payments_created_at"), "payments", ["created_at"], unique=False)
    op.create_index(op.f("ix_payments_customer_id"), "payments", ["customer_id"], unique=False)
    op.create_index(op.f("ix_payments_payment_date"), "payments", ["payment_date"], unique=False)
    op.create_index(op.f("ix_payments_payment_reference"), "payments", ["payment_reference"], unique=True)
    op.create_index(op.f("ix_payments_status"), "payments", ["status"], unique=False)
    op.create_index(op.f("ix_payments_transaction_reference"), "payments", ["transaction_reference"], unique=False)

    op.create_table(
        "payment_allocations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("payment_id", sa.String(length=36), nullable=False),
        sa.Column("invoice_id", sa.String(length=36), nullable=False),
        sa.Column("allocated_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("allocation_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.String(length=300), nullable=True),
        sa.Column("allocated_by", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["allocated_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payment_id", "invoice_id", name="uq_payment_invoice_allocation"),
    )
    op.create_index(op.f("ix_payment_allocations_allocation_date"), "payment_allocations", ["allocation_date"], unique=False)
    op.create_index(op.f("ix_payment_allocations_invoice_id"), "payment_allocations", ["invoice_id"], unique=False)
    op.create_index(op.f("ix_payment_allocations_payment_id"), "payment_allocations", ["payment_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_payment_allocations_payment_id"), table_name="payment_allocations")
    op.drop_index(op.f("ix_payment_allocations_invoice_id"), table_name="payment_allocations")
    op.drop_index(op.f("ix_payment_allocations_allocation_date"), table_name="payment_allocations")
    op.drop_table("payment_allocations")

    op.drop_index(op.f("ix_payments_transaction_reference"), table_name="payments")
    op.drop_index(op.f("ix_payments_status"), table_name="payments")
    op.drop_index(op.f("ix_payments_payment_reference"), table_name="payments")
    op.drop_index(op.f("ix_payments_payment_date"), table_name="payments")
    op.drop_index(op.f("ix_payments_customer_id"), table_name="payments")
    op.drop_index(op.f("ix_payments_created_at"), table_name="payments")
    op.drop_table("payments")

    op.drop_index(op.f("ix_production_expenses_status"), table_name="production_expenses")
    op.drop_index(op.f("ix_production_expenses_production_run_id"), table_name="production_expenses")
    op.drop_index(op.f("ix_production_expenses_expense_number"), table_name="production_expenses")
    op.drop_index(op.f("ix_production_expenses_expense_date"), table_name="production_expenses")
    op.drop_index(op.f("ix_production_expenses_category"), table_name="production_expenses")
    op.drop_table("production_expenses")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        sa.Enum(name="customer_payment_status_enum").drop(bind, checkfirst=True)
        sa.Enum(name="customer_payment_method_enum").drop(bind, checkfirst=True)
        sa.Enum(name="production_expense_status_enum").drop(bind, checkfirst=True)
        sa.Enum(name="production_expense_category_enum").drop(bind, checkfirst=True)
