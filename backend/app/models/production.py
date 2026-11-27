from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
import uuid

from sqlalchemy import (
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.stock_item import StockItemType


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ProductionStatus(str, Enum):
    DRAFT = "DRAFT"
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    POSTED = "POSTED"
    CANCELLED = "CANCELLED"


class ProductionRun(Base):
    """Manufacturing batch execution document linked to an immutable BOM version."""

    __tablename__ = "production_runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    order_number: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    bom_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("bom_headers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    bom_version_snapshot: Mapped[int] = mapped_column(Integer, nullable=False)
    batch_number: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    production_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    planned_batches: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=Decimal("1.000000")
    )
    expected_output: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    actual_good_output: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=Decimal("0.000000")
    )
    damaged_packets: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=Decimal("0.000000")
    )
    damaged_pouches: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=Decimal("0.000000")
    )
    scrap_quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=Decimal("0.000000")
    )
    yield_variance_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    variance_tolerance_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("3.00")
    )
    supervisor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ProductionStatus] = mapped_column(
        SAEnum(
            ProductionStatus,
            name="production_status_enum",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        default=ProductionStatus.DRAFT,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    posted_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    product = relationship("Product", foreign_keys=[product_id], lazy="joined")
    bom = relationship("BomHeader", foreign_keys=[bom_id], lazy="joined")
    supervisor = relationship("User", foreign_keys=[supervisor_id], lazy="joined")
    materials = relationship(
        "ProductionMaterial",
        back_populates="production_run",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    outputs = relationship(
        "ProductionOutput",
        back_populates="production_run",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    wastages = relationship(
        "ProductionWastage",
        back_populates="production_run",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ProductionMaterial(Base):
    """Planned vs actual material and packaging consumption for a production run."""

    __tablename__ = "production_materials"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    production_run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("production_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stock_item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("stock_items.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    input_category: Mapped[StockItemType] = mapped_column(
        SAEnum(
            StockItemType,
            name="stock_item_type_enum",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
            create_type=False,
        ),
        nullable=False,
    )
    unit_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("units.id", ondelete="RESTRICT"), nullable=False
    )
    planned_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    planned_base_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    actual_quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=Decimal("0.000000")
    )
    damaged_quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=Decimal("0.000000")
    )
    total_consumed_base_qty: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=Decimal("0.000000")
    )
    variance_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    variance_status: Mapped[str | None] = mapped_column(String(16), nullable=True)

    production_run = relationship("ProductionRun", back_populates="materials")
    stock_item = relationship("StockItem", foreign_keys=[stock_item_id], lazy="joined")
    unit = relationship("Unit", foreign_keys=[unit_id], lazy="joined")


class ProductionOutput(Base):
    """Finished goods output record with carton capacity check."""

    __tablename__ = "production_outputs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    production_run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("production_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    unit_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("units.id", ondelete="RESTRICT"), nullable=False
    )
    expected_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    good_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    damaged_packets: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=Decimal("0.000000")
    )
    cartons_used: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=Decimal("0.000000")
    )
    carton_capacity_packets: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=Decimal("0.000000")
    )
    unpacked_packets: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=Decimal("0.000000")
    )
    packaging_warning: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    production_run = relationship("ProductionRun", back_populates="outputs")
    product = relationship("Product", foreign_keys=[product_id], lazy="joined")
    unit = relationship("Unit", foreign_keys=[unit_id], lazy="joined")
    recorder = relationship("User", foreign_keys=[recorded_by], lazy="joined")


class ProductionWastage(Base):
    """Recorded scrap, damaged pouches, damaged packets, and process loss."""

    __tablename__ = "production_wastage"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    production_run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("production_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stock_item_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("stock_items.id", ondelete="RESTRICT"), nullable=True
    )
    wastage_type: Mapped[str] = mapped_column(String(40), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    unit_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("units.id", ondelete="RESTRICT"), nullable=True
    )
    reason: Mapped[str] = mapped_column(String(250), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    production_run = relationship("ProductionRun", back_populates="wastages")
    stock_item = relationship("StockItem", foreign_keys=[stock_item_id], lazy="joined")
    unit = relationship("Unit", foreign_keys=[unit_id], lazy="joined")
    recorder = relationship("User", foreign_keys=[recorded_by], lazy="joined")
