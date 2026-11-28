"""Idempotent demo database initialization and benchmark seed script.

Safety guard: Requires explicit non-production demo mode (`DEMO_SEED_ENABLED=true` or `--force-demo`).
Populates dummy evaluation accounts only:
- Factory Admin (`admin@factoryflow.io`)
- Salesman A (`orders@factoryflow.io`)
- Salesman B (`salesman_b@factoryflow.io`)
- Production Supervisor (`floor@factoryflow.io`)
- QA Inspector (`qa@factoryflow.io`)
- Accountant / Auditor (`auditor@factoryflow.io`)
- Factory Owner (`owner@factoryflow.io`)
"""

import argparse

from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.database import Base, SessionLocal, check_database_connection, engine
from app.core.permissions import Role
from app.models import (  # noqa: F401
    AuditLog,
    BomHeader,
    BomLine,
    Customer,
    Product,
    ProductionMaterial,
    ProductionOutput,
    ProductionRun,
    ProductionWastage,
    Purchase,
    PurchaseItem,
    StockAdjustment,
    StockBalance,
    StockItem,
    StockLedger,
    Supplier,
    Unit,
    UnitConversion,
    User,
)
from app.schemas.user import UserCreate
from app.services.master_seed_service import seed_benchmark_master_data
from app.services.phase3_seed_service import seed_phase3_benchmark_data
from app.services.phase4_seed_service import seed_benchmark_bom
from app.services.user_service import DEFAULT_SEED_USERS, create_user, seed_default_users

EXTRA_DEMO_USERS = [
    ("salesman_b@factoryflow.io", "Salesman B (Demo)", "Field Sales", Role.ORDER_MANAGER),
]


def seed_extra_demo_accounts(db, password: str) -> int:
    created = 0
    for email, full_name, department, role in EXTRA_DEMO_USERS:
        existing = db.scalar(select(User).where(func.lower(User.email) == email.lower()))
        if existing is None:
            create_user(
                db,
                UserCreate(
                    email=email,
                    full_name=full_name,
                    department=department,
                    role=role,
                    password=password,
                ),
            )
            created += 1
    return created


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed FactoryFlow demo environment idempotently.")
    parser.add_argument(
        "--force-demo",
        action="store_true",
        help="Confirm explicit demo seeding when DEMO_SEED_ENABLED is false.",
    )
    args = parser.parse_args()

    settings = get_settings()
    if settings.is_production and not settings.seed_default_users:
        raise RuntimeError(
            "Refusing demo seed in ENVIRONMENT=production without explicit DEMO_SEED_ENABLED=true."
        )
    if not settings.seed_default_users and not args.force_demo:
        raise RuntimeError(
            "Set DEMO_SEED_ENABLED=true or pass --force-demo to populate dummy demo accounts."
        )
    if settings.is_production and (
        settings.seed_default_password.strip()
        in {"", "FactoryFlow!2026", "replace-with-custom-non-default-demo-password"}
        or len(settings.seed_default_password.strip()) < 12
    ):
        raise RuntimeError(
            "Refusing hosted demo seed with default or placeholder DEMO_SEED_PASSWORD. "
            "Configure a unique custom DEMO_SEED_PASSWORD (>=12 chars) first."
        )

    print("Connecting to database...")
    with SessionLocal() as db:
        if not check_database_connection(db):
            raise RuntimeError("Database connection failed. Verify DATABASE_URL configuration.")

    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        users_created = seed_default_users(db, settings.seed_default_password)
        extra_created = seed_extra_demo_accounts(db, settings.seed_default_password)
        master_counts = seed_benchmark_master_data(db)
        phase3_counts = seed_phase3_benchmark_data(db, post_benchmark_purchase=True)
        phase4_counts = seed_benchmark_bom(db)
        print(
            f"Demo seed complete. Base roles created: {users_created}/{len(DEFAULT_SEED_USERS)}; "
            f"Additional evaluator accounts created: {extra_created}/{len(EXTRA_DEMO_USERS)}."
        )
        print(f"Master data created: {master_counts}")
        print(f"Benchmark inventory & purchase created: {phase3_counts}")
        print(f"Benchmark BOM created: {phase4_counts}")


if __name__ == "__main__":
    main()
