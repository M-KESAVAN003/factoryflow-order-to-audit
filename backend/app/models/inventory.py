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
    event,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MovementType(str, Enum):
    """Canonical append-only stock ledger movement types."""

    OPENING_STOCK = "OPENING_STOCK"
    PURCHASE_RECEIPT = "PURCHASE_RECEIPT"
    PRODUCTION_ISSUE = "PRODUCTION_ISSUE"
    PRODUCTION_OUTPUT = "PRODUCTION_OUTPUT"
    SALES_DISPATCH = "SALES_DISPATCH"
    SALES_RETURN = "SALES_RETURN"
    PURCHASE_RETURN = "PURCHASE_RETURN"
    STOCK_ADJUSTMENT = "STOCK_ADJUSTMENT"
    REVERSAL = "REVERSAL"


class AdjustmentStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"


class StockBalance(Base):
    """Performance projection of current stock & weighted-average cost per StockItem."""

    __tablename__ = "stock_balances"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    stock_item_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("stock_items.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
        index=True,
    )
    available_quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=Decimal("0.000000")
    )
    average_cost: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=Decimal("0.000000")
    )
    total_value: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0.0000")
    )
    last_movement_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    stock_item = relationship("StockItem", foreign_keys=[stock_item_id], lazy="joined")


class StockLedger(Base):
    """Append-only source-of-truth ledger recording every inventory movement and valuation."""

    __tablename__ = "stock_ledger"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    stock_item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("stock_items.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    movement_type: Mapped[MovementType] = mapped_column(
        SAEnum(
            MovementType,
            name="stock_movement_type_enum",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        index=True,
    )
    quantity_in: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=Decimal("0.000000")
    )
    quantity_out: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=Decimal("0.000000")
    )
    base_unit_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("units.id", ondelete="RESTRICT"), nullable=False
    )
    reference_doc_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    reference_doc_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    transaction_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, index=True
    )
    unit_cost: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=Decimal("0.000000")
    )
    total_value: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0.0000")
    )
    balance_qty_after: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=Decimal("0.000000")
    )
    avg_cost_after: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=Decimal("0.000000")
    )
    balance_value_after: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0.0000")
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, index=True
    )

    stock_item = relationship("StockItem", foreign_keys=[stock_item_id], lazy="joined")
    base_unit = relationship("Unit", foreign_keys=[base_unit_id], lazy="joined")
    creator = relationship("User", foreign_keys=[created_by], lazy="joined")


@event.listens_for(StockLedger, "before_update")
def _prevent_ledger_update(mapper, connection, target) -> None:  # noqa: ARG001
    raise ValueError("StockLedger entries are immutable and cannot be modified.")


@event.listens_for(StockLedger, "before_delete")
def _prevent_ledger_delete(mapper, connection, target) -> None:  # noqa: ARG001
    raise ValueError("StockLedger entries are append-only and cannot be deleted.")


class StockAdjustment(Base):
    """Controlled physical-count stock adjustment requiring reason and approval."""

    __tablename__ = "stock_adjustments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    stock_item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("stock_items.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    current_balance: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    physical_count: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    difference: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    reason: Mapped[str] = mapped_column(String(200), nullable=False)
    supporting_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[AdjustmentStatus] = mapped_column(
        SAEnum(
            AdjustmentStatus,
            name="stock_adjustment_status_enum",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        default=AdjustmentStatus.PENDING,
        index=True,
    )
    adjustment_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    approved_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    stock_item = relationship("StockItem", foreign_keys=[stock_item_id], lazy="joined")
    creator = relationship("User", foreign_keys=[created_by], lazy="joined")
    approver = relationship("User", foreign_keys=[approved_by], lazy="joined")
