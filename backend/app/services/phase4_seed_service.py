from datetime import date
from decimal import Decimal
from typing import Dict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.permissions import Role
from app.models.bom import BomHeader
from app.models.product import Product
from app.models.stock_item import StockItem
from app.models.user import User
from app.schemas.bom_production import BomCreate, BomLineInput
from app.services.bom_service import create_bom


def seed_benchmark_bom(db: Session) -> Dict[str, int]:
    """Idempotently seed the Phase 4 Benchmark BOM v1 for Murukku 200 g (200 packets/batch)."""
    actor = db.scalar(select(User).where(User.role == Role.ADMIN).limit(1))
    if actor is None:
        raise RuntimeError("Admin user must exist before seeding BOM.")

    murukku = db.scalar(select(Product).where(func.upper(Product.sku) == "MUR-200"))
    if murukku is None:
        return {"boms_created": 0}

    existing_bom = db.scalar(
        select(BomHeader).where(BomHeader.product_id == murukku.id).limit(1)
    )
    if existing_bom is not None:
        return {"boms_created": 0}

    specs = [
        ("RM-FLOUR", Decimal("40.000000")),
        ("RM-OIL", Decimal("10.000000")),
        ("RM-SPICE", Decimal("1.200000")),
        ("PKG-POUCH-200", Decimal("200.000000")),
        ("PKG-CARTON", Decimal("10.000000")),
    ]
    lines = []
    for sku, qty in specs:
        item = db.scalar(select(StockItem).where(func.upper(StockItem.sku) == sku))
        if item is None:
            raise RuntimeError(f"Required benchmark StockItem '{sku}' missing.")
        lines.append(
            BomLineInput(
                stock_item_id=item.id,
                standard_quantity=qty,
                unit_id=item.base_unit_id,
            )
        )

    create_bom(
        db,
        BomCreate(
            product_id=murukku.id,
            batch_size=Decimal("1.000000"),
            expected_output=Decimal("200.000000"),
            output_unit_id=murukku.unit_id,
            effective_date=date.today(),
            notes="Benchmark Murukku 200 g formulation (1 batch = 200 packets; 1 carton = 20 packets)",
            activate=True,
            lines=lines,
        ),
        actor=actor,
    )
    return {"boms_created": 1}
