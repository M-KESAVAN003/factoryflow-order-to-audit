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
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.stock_item import StockItemType


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BomStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class BomHeader(Base):
    """Versioned Bill of Materials header for a finished Product."""

    __tablename__ = "bom_headers"
    __table_args__ = (
        UniqueConstraint("product_id", "version_number", name="uq_bom_product_version"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    batch_size: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=Decimal("1.000000")
    )
    expected_output: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    output_unit_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("units.id", ondelete="RESTRICT"), nullable=False
    )
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[BomStatus] = mapped_column(
        SAEnum(
            BomStatus,
            name="bom_status_enum",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        default=BomStatus.DRAFT,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    product = relationship("Product", foreign_keys=[product_id], lazy="joined")
    output_unit = relationship("Unit", foreign_keys=[output_unit_id], lazy="joined")
    creator = relationship("User", foreign_keys=[created_by], lazy="joined")
    lines = relationship(
        "BomLine",
        back_populates="bom",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class BomLine(Base):
    """Standard raw material or packaging input required per BOM batch."""

    __tablename__ = "bom_lines"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    bom_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("bom_headers.id", ondelete="CASCADE"), nullable=False, index=True
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
    standard_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    unit_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("units.id", ondelete="RESTRICT"), nullable=False
    )
    base_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)

    bom = relationship("BomHeader", back_populates="lines")
    stock_item = relationship("StockItem", foreign_keys=[stock_item_id], lazy="joined")
    unit = relationship("Unit", foreign_keys=[unit_id], lazy="joined")
