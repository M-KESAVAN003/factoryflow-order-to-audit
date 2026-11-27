from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
import uuid

from sqlalchemy import (
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ExpenseCategory(str, Enum):
    """Canonical overhead / conversion expense categories on production runs."""

    LABOUR = "LABOUR"
    GAS = "GAS"
    ELECTRICITY = "ELECTRICITY"
    POWER = "POWER"
    MAINTENANCE = "MAINTENANCE"
    OTHER_OVERHEAD = "OTHER_OVERHEAD"


class ExpenseStatus(str, Enum):
    DRAFT = "DRAFT"
    POSTED = "POSTED"
    REVERSED = "REVERSED"


class CustomerPaymentMethod(str, Enum):
    CASH = "CASH"
    BANK_TRANSFER = "BANK_TRANSFER"
    UPI = "UPI"
    CHEQUE = "CHEQUE"
    OTHER = "OTHER"


class CustomerPaymentStatus(str, Enum):
    DRAFT = "DRAFT"
    POSTED = "POSTED"
    REVERSED = "REVERSED"


class ProductionExpense(Base):
    """Production run conversion/overhead expense with draft -> posted -> reversible lifecycle."""

    __tablename__ = "production_expenses"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    expense_number: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    production_run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("production_runs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    category: Mapped[ExpenseCategory] = mapped_column(
        SAEnum(
            ExpenseCategory,
            name="production_expense_category_enum",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(String(250), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[ExpenseStatus] = mapped_column(
        SAEnum(
            ExpenseStatus,
            name="production_expense_status_enum",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        default=ExpenseStatus.DRAFT,
        index=True,
    )
    reversal_of_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("production_expenses.id", ondelete="RESTRICT"), nullable=True
    )
    recorded_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    posted_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    production_run = relationship("ProductionRun", foreign_keys=[production_run_id], lazy="joined")
    recorder = relationship("User", foreign_keys=[recorded_by], lazy="joined")


@event.listens_for(ProductionExpense, "before_delete")
def _prevent_expense_delete(mapper, connection, target) -> None:  # noqa: ARG001
    raise ValueError("ProductionExpense records cannot be deleted; post a reversal instead.")


class Payment(Base):
    """Customer payment receipt with unallocated advance and immutable history."""

    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    payment_reference: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    customer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    payment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    payment_method: Mapped[CustomerPaymentMethod] = mapped_column(
        SAEnum(
            CustomerPaymentMethod,
            name="customer_payment_method_enum",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
    )
    amount_received: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    allocated_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )
    unallocated_advance: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )
    transaction_reference: Mapped[str | None] = mapped_column(
        String(120), nullable=True, index=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[CustomerPaymentStatus] = mapped_column(
        SAEnum(
            CustomerPaymentStatus,
            name="customer_payment_status_enum",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        default=CustomerPaymentStatus.POSTED,
        index=True,
    )
    reversal_of_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("payments.id", ondelete="RESTRICT"), nullable=True
    )
    recorded_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    customer = relationship("Customer", foreign_keys=[customer_id], lazy="joined")
    recorder = relationship("User", foreign_keys=[recorded_by], lazy="joined")
    allocations = relationship(
        "PaymentAllocation",
        back_populates="payment",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


@event.listens_for(Payment, "before_delete")
def _prevent_payment_delete(mapper, connection, target) -> None:  # noqa: ARG001
    raise ValueError("Customer payment records are immutable and cannot be deleted.")


class PaymentAllocation(Base):
    """Allocation mapping a customer Payment to one or more posted GST Invoices."""

    __tablename__ = "payment_allocations"
    __table_args__ = (
        UniqueConstraint("payment_id", "invoice_id", name="uq_payment_invoice_allocation"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    payment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("payments.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    invoice_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("invoices.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    allocated_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    allocation_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(String(300), nullable=True)
    allocated_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    payment = relationship("Payment", back_populates="allocations")
    invoice = relationship("Invoice", foreign_keys=[invoice_id], lazy="joined")
    allocator = relationship("User", foreign_keys=[allocated_by], lazy="joined")


@event.listens_for(PaymentAllocation, "before_delete")
def _prevent_allocation_delete(mapper, connection, target) -> None:  # noqa: ARG001
    raise ValueError("Payment allocations cannot be deleted; issue a reversal payment instead.")
