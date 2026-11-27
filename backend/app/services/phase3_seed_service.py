from datetime import date
from decimal import Decimal
from typing import Dict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.permissions import Role
from app.models.inventory import MovementType, StockLedger
from app.models.purchase import PaymentStatus, Purchase
from app.models.stock_item import StockItem
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.inventory_purchase import PurchaseCreate, PurchaseItemInput
from app.services.ledger_service import apply_stock_movement
from app.services.purchase_service import create_purchase, post_purchase

OPENING_BENCHMARK_SPECS = [
    ("RM-FLOUR", Decimal("100.000000"), Decimal("42.000000")),
    ("RM-OIL", Decimal("30.000000"), Decimal("140.000000")),
    ("RM-SPICE", Decimal("5.000000"), Decimal("200.000000")),
    ("PKG-POUCH-200", Decimal("500.000000"), Decimal("2.500000")),
    ("PKG-CARTON", Decimal("30.000000"), Decimal("15.000000")),
    ("MUR-200", Decimal("50.000000"), Decimal("0.000000")),
]


def seed_opening_inventory(db: Session, *, actor: User | None = None) -> int:
    """Idempotently record OPENING_STOCK ledger entries for all benchmark items."""
    created = 0
    actor_id = actor.id if actor else None

    for sku, qty, rate in OPENING_BENCHMARK_SPECS:
        item = db.scalar(select(StockItem).where(func.upper(StockItem.sku) == sku))
        if item is None:
            continue

        existing_opening = db.scalar(
            select(StockLedger).where(
                StockLedger.stock_item_id == item.id,
                StockLedger.movement_type == MovementType.OPENING_STOCK,
            )
        )
        if existing_opening is not None:
            continue

        apply_stock_movement(
            db,
            stock_item=item,
            movement_type=MovementType.OPENING_STOCK,
            quantity_in=qty,
            unit_cost=rate,
            reference_doc_type="OPENING_SEED",
            reference_doc_id=f"OPEN-{sku}",
            notes=f"Benchmark opening inventory for {item.name}",
            created_by=actor_id,
        )
        created += 1

    if created:
        db.commit()
    return created


def seed_phase3_benchmark_data(
    db: Session,
    *,
    post_benchmark_purchase: bool = True,
) -> Dict[str, int]:
    """Idempotently seed Phase 3 opening inventory and BENCHMARK-FLOUR-001 purchase."""
    actor = db.scalar(select(User).where(User.role == Role.ADMIN).limit(1))
    if actor is None:
        raise RuntimeError("Admin user must exist before seeding Phase 3 benchmark data.")

    opening_created = seed_opening_inventory(db, actor=actor)
    purchases_created = 0

    existing_purchase = db.scalar(
        select(Purchase).where(Purchase.reference_number == "BENCHMARK-FLOUR-001")
    )
    if existing_purchase is None:
        supplier = db.scalar(
            select(Supplier).where(Supplier.name == "Benchmark Supplier").limit(1)
        )
        flour = db.scalar(select(StockItem).where(StockItem.sku == "RM-FLOUR"))
        if supplier and flour:
            purchase = create_purchase(
                db,
                PurchaseCreate(
                    reference_number="BENCHMARK-FLOUR-001",
                    supplier_id=supplier.id,
                    purchase_date=date.today(),
                    payment_status=PaymentStatus.PAID,
                    notes="Internship benchmark flour purchase (60 kg at INR 45/kg)",
                    items=[
                        PurchaseItemInput(
                            stock_item_id=flour.id,
                            unit_id=flour.base_unit_id,
                            quantity=Decimal("60.000000"),
                            unit_rate=Decimal("45.000000"),
                            tax_rate=Decimal("0.00"),
                        )
                    ],
                ),
                actor=actor,
            )
            purchases_created += 1
            if post_benchmark_purchase:
                post_purchase(db, purchase.id, actor=actor)

    return {
        "opening_entries": opening_created,
        "benchmark_purchases": purchases_created,
    }
