from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
import uuid

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
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


class SalesOrderStatus(str, Enum):
    """Canonical lifecycle states for mobile sales orders through dispatch."""

    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    AWAITING_STOCK = "AWAITING_STOCK"
    PARTIALLY_FULFILLED = "PARTIALLY_FULFILLED"
    INVOICED = "INVOICED"
    DISPATCHED = "DISPATCHED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class TaxType(str, Enum):
    """GST supply classification derived from factory vs customer state."""

    INTRA_STATE = "INTRA_STATE"
    INTER_STATE = "INTER_STATE"


class InvoiceStatus(str, Enum):
    POSTED = "POSTED"


class SalesOrder(Base):
    """Customer sales order submitted by Salesman and reviewed/fulfilled by Admin."""

    __tablename__ = "sales_orders"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    order_number: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    customer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    salesman_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    order_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[SalesOrderStatus] = mapped_column(
        SAEnum(
            SalesOrderStatus,
            name="sales_order_status_enum",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        default=SalesOrderStatus.SUBMITTED,
        index=True,
    )
    factory_state: Mapped[str] = mapped_column(String(80), nullable=False)
    customer_state: Mapped[str] = mapped_column(String(80), nullable=False)
    place_of_supply: Mapped[str] = mapped_column(String(80), nullable=False)
    tax_type: Mapped[TaxType] = mapped_column(
        SAEnum(
            TaxType,
            name="gst_tax_type_enum",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
    )
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )
    cgst_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )
    sgst_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )
    igst_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )
    has_stock_shortage: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    shortage_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Phase 8 offline PWA synchronization metadata & idempotency
    idempotency_key: Mapped[str | None] = mapped_column(
        String(128), unique=True, index=True, nullable=True
    )
    local_order_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    is_offline_order: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    offline_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    price_review_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    price_conflict_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    reviewed_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    customer = relationship("Customer", foreign_keys=[customer_id], lazy="joined")
    salesman = relationship("User", foreign_keys=[salesman_id], lazy="joined")
    items = relationship(
        "SalesOrderItem",
        back_populates="sales_order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    invoice = relationship("Invoice", back_populates="sales_order", uselist=False, lazy="joined")
    dispatch = relationship("Dispatch", back_populates="sales_order", uselist=False, lazy="joined")


class SalesOrderItem(Base):
    """Product line item with GST rate and requested vs approved vs dispatched quantities."""

    __tablename__ = "sales_order_items"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    sales_order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    stock_item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("stock_items.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    unit_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("units.id", ondelete="RESTRICT"), nullable=False
    )
    hsn_code: Mapped[str] = mapped_column(String(20), nullable=False)
    requested_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    approved_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    dispatched_quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=Decimal("0.000000")
    )
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    submitted_unit_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    gst_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    taxable_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    cgst_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("0.00")
    )
    sgst_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("0.00")
    )
    igst_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("0.00")
    )
    cgst_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )
    sgst_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )
    igst_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )
    line_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    sales_order = relationship("SalesOrder", back_populates="items")
    product = relationship("Product", foreign_keys=[product_id], lazy="joined")
    stock_item = relationship("StockItem", foreign_keys=[stock_item_id], lazy="joined")
    unit = relationship("Unit", foreign_keys=[unit_id], lazy="joined")


class Invoice(Base):
    """Immutable posted GST Tax Invoice linked to a unique SalesOrder and FY sequence."""

    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("financial_year", "sequence_number", name="uq_invoice_fy_sequence"),
        UniqueConstraint("sales_order_id", name="uq_invoice_sales_order"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    invoice_number: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    financial_year: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    sales_order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sales_orders.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    customer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[InvoiceStatus] = mapped_column(
        SAEnum(
            InvoiceStatus,
            name="invoice_status_enum",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        default=InvoiceStatus.POSTED,
    )

    # Immutable snapshots for regulatory GST compliance
    factory_name: Mapped[str] = mapped_column(String(150), nullable=False)
    factory_address: Mapped[str] = mapped_column(Text, nullable=False)
    factory_gstin: Mapped[str] = mapped_column(String(15), nullable=False)
    factory_state: Mapped[str] = mapped_column(String(80), nullable=False)
    factory_state_code: Mapped[str] = mapped_column(String(5), nullable=False)

    customer_name: Mapped[str] = mapped_column(String(150), nullable=False)
    customer_gstin: Mapped[str] = mapped_column(String(15), nullable=False)
    billing_address: Mapped[str] = mapped_column(Text, nullable=False)
    customer_state: Mapped[str] = mapped_column(String(80), nullable=False)
    place_of_supply: Mapped[str] = mapped_column(String(80), nullable=False)

    tax_type: Mapped[TaxType] = mapped_column(
        SAEnum(
            TaxType,
            name="gst_tax_type_enum",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
            create_type=False,
        ),
        nullable=False,
    )
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    cgst_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    sgst_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    igst_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    grand_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    amount_in_words: Mapped[str] = mapped_column(String(300), nullable=False)

    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, index=True
    )

    sales_order = relationship("SalesOrder", back_populates="invoice")
    creator = relationship("User", foreign_keys=[created_by], lazy="joined")
    items = relationship(
        "InvoiceItem",
        back_populates="invoice",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    credit_notes = relationship("CreditNote", back_populates="invoice", lazy="selectin")
    dispatch = relationship("Dispatch", back_populates="invoice", uselist=False, lazy="joined")


@event.listens_for(Invoice, "before_update")
def _prevent_invoice_update(mapper, connection, target) -> None:  # noqa: ARG001
    raise ValueError("Posted invoices are immutable; issue a traceable CreditNote for corrections.")


@event.listens_for(Invoice, "before_delete")
def _prevent_invoice_delete(mapper, connection, target) -> None:  # noqa: ARG001
    raise ValueError("Posted invoices cannot be deleted; issue a CreditNote for reversals.")


class InvoiceItem(Base):
    """Line item snapshot preserved inside a posted GST invoice."""

    __tablename__ = "invoice_items"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    invoice_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sales_order_item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sales_order_items.id", ondelete="RESTRICT"), nullable=False
    )
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    product_name: Mapped[str] = mapped_column(String(150), nullable=False)
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    pack_size: Mapped[str] = mapped_column(String(60), nullable=False)
    hsn_code: Mapped[str] = mapped_column(String(20), nullable=False)
    unit_symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    gst_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    taxable_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    cgst_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    sgst_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    igst_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    cgst_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    sgst_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    igst_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    invoice = relationship("Invoice", back_populates="items")


class CreditNote(Base):
    """Traceable credit note reversal linked to an immutable posted Invoice."""

    __tablename__ = "credit_notes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    credit_note_number: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    invoice_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("invoices.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    financial_year: Mapped[str] = mapped_column(String(16), nullable=False)
    credit_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    invoice = relationship("Invoice", back_populates="credit_notes")
    creator = relationship("User", foreign_keys=[created_by], lazy="joined")


class Dispatch(Base):
    """Physical finished-goods dispatch linked 1:1 to a SalesOrder & Invoice and StockLedger."""

    __tablename__ = "dispatches"
    __table_args__ = (
        UniqueConstraint("sales_order_id", name="uq_dispatch_sales_order"),
        UniqueConstraint("invoice_id", name="uq_dispatch_invoice"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    dispatch_number: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    sales_order_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sales_orders.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    invoice_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("invoices.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    dispatch_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    vehicle_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    transporter_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    dispatched_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, index=True
    )

    sales_order = relationship("SalesOrder", back_populates="dispatch")
    invoice = relationship("Invoice", back_populates="dispatch")
    dispatcher = relationship("User", foreign_keys=[dispatched_by], lazy="joined")
    items = relationship(
        "DispatchItem",
        back_populates="dispatch",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class DispatchItem(Base):
    """Dispatched product quantity linked directly to its StockLedger SALES_DISPATCH entry."""

    __tablename__ = "dispatch_items"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    dispatch_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("dispatches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sales_order_item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sales_order_items.id", ondelete="RESTRICT"), nullable=False
    )
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    stock_item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("stock_items.id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    stock_ledger_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("stock_ledger.id", ondelete="RESTRICT"), nullable=False
    )

    dispatch = relationship("Dispatch", back_populates="items")
    product = relationship("Product", foreign_keys=[product_id], lazy="joined")
    stock_ledger = relationship("StockLedger", foreign_keys=[stock_ledger_id], lazy="joined")
