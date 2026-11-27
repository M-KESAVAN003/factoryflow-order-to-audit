from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
import uuid

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UnitDimension(str, Enum):
    """Physical measurement dimensions for validating unit conversions."""

    MASS = "mass"
    VOLUME = "volume"
    COUNT = "count"


class Unit(Base):
    """Canonical unit of measure (kg, g, litre, ml, piece, packet, carton)."""

    __tablename__ = "units"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    dimension: Mapped[UnitDimension] = mapped_column(
        SAEnum(
            UnitDimension,
            name="unit_dimension_enum",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
    )
    is_base: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )


class UnitConversion(Base):
    """Dimensional conversion factor between two units, optionally scoped to a product."""

    __tablename__ = "unit_conversions"
    __table_args__ = (
        UniqueConstraint(
            "from_unit_id",
            "to_unit_id",
            "product_id",
            name="uq_unit_conversion_pair_product",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    from_unit_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("units.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    to_unit_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("units.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    product_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=True, index=True
    )
    conversion_factor: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    from_unit = relationship("Unit", foreign_keys=[from_unit_id], lazy="joined")
    to_unit = relationship("Unit", foreign_keys=[to_unit_id], lazy="joined")
    product = relationship("Product", foreign_keys=[product_id], lazy="joined")
