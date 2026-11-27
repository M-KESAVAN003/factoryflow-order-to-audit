from datetime import datetime, timezone
from decimal import Decimal
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Product(Base):
    """Sellable finished good master linked 1:1 with a FINISHED_GOOD StockItem."""

    __tablename__ = "products"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    pack_size: Mapped[str] = mapped_column(String(60), nullable=False)
    selling_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    gst_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    hsn_code: Mapped[str] = mapped_column(String(20), nullable=False)
    unit_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("units.id", ondelete="RESTRICT"), nullable=False
    )
    stock_item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("stock_items.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    pouch_stock_item_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("stock_items.id", ondelete="SET NULL"), nullable=True
    )
    carton_stock_item_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("stock_items.id", ondelete="SET NULL"), nullable=True
    )
    packets_per_carton: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    unit = relationship("Unit", foreign_keys=[unit_id], lazy="joined")
    stock_item = relationship("StockItem", foreign_keys=[stock_item_id], lazy="joined")
    pouch_stock_item = relationship("StockItem", foreign_keys=[pouch_stock_item_id], lazy="joined")
    carton_stock_item = relationship("StockItem", foreign_keys=[carton_stock_item_id], lazy="joined")
