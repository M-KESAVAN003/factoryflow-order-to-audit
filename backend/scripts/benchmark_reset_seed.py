"""Isolated Benchmark Test Database Reset & Seed Command (Phase 9).

Safety guarantees:
- NEVER runs against production (`ENVIRONMENT=production`).
- NEVER runs against the active main `DATABASE_URL`.
- For PostgreSQL targets, requires the database name to include 'test', 'benchmark', or 'qa'.
"""

import argparse
from decimal import Decimal
import os
from urllib.parse import urlparse

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.database import Base, build_engine, normalize_database_url
from app.services.master_seed_service import seed_benchmark_master_data
from app.services.phase3_seed_service import seed_opening_inventory
from app.services.phase4_seed_service import seed_benchmark_bom
from app.services.user_service import seed_default_users


def validate_safe_test_database_url(target_url: str) -> str:
    """Enforce strict safety guards preventing accidental execution on prod/main DBs."""
    env_name = os.getenv("ENVIRONMENT", "").strip().lower()
    if env_name in {"production", "prod"}:
        raise RuntimeError("SAFETY BLOCK: Refusing to reset/seed when ENVIRONMENT is production.")

    normalized_target = normalize_database_url(target_url)
    if "ep-example.neon.tech" in normalized_target or "change_me" in normalized_target:
        raise RuntimeError("Refusing placeholder URL; provide a real isolated test database URL.")

    main_env_url = os.getenv("DATABASE_URL")
    if main_env_url and normalize_database_url(main_env_url) == normalized_target:
        raise RuntimeError("SAFETY BLOCK: Target URL matches main DATABASE_URL.")

    settings = get_settings()
    if normalize_database_url(settings.database_url) == normalized_target:
        raise RuntimeError("SAFETY BLOCK: Target URL matches configured application database_url.")

    if not normalized_target.startswith("sqlite"):
        db_name = urlparse(normalized_target).path.lstrip("/").lower()
        if not any(tok in db_name for tok in ("test", "benchmark", "qa")):
            raise RuntimeError(
                f"SAFETY BLOCK: PostgreSQL target database '{db_name}' must contain 'test', 'benchmark', or 'qa'."
            )
    return normalized_target


def reset_and_seed_benchmark_db(database_url: str, *, use_alembic: bool = True) -> dict:
    """Drop all objects in the isolated test DB, migrate to head, and idempotently seed benchmark masters."""
    safe_url = validate_safe_test_database_url(database_url)
    engine = build_engine(database_url=safe_url)
    try:
        Base.metadata.drop_all(bind=engine)
        if use_alembic:
            cfg = Config("alembic.ini")
            cfg.set_main_option("sqlalchemy.url", safe_url)
            with engine.begin() as conn:
                if safe_url.startswith("sqlite"):
                    pass
                else:
                    conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
            command.upgrade(cfg, "head")
        else:
            Base.metadata.create_all(bind=engine)

        SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
        with SessionLocal() as db:
            settings = get_settings()
            users_1 = seed_default_users(db, settings.seed_default_password)
            master_1 = seed_benchmark_master_data(db)
            open_1 = seed_opening_inventory(db)
            bom_1 = seed_benchmark_bom(db)

            # Second pass verifies idempotency
            users_2 = seed_default_users(db, settings.seed_default_password)
            master_2 = seed_benchmark_master_data(db)
            open_2 = seed_opening_inventory(db)
            bom_2 = seed_benchmark_bom(db)

            assert users_2 == 0
            assert all(v == 0 for v in master_2.values())
            assert open_2 == 0
            assert bom_2["boms_created"] == 0

            return {
                "database_url": "sqlite-isolated" if safe_url.startswith("sqlite") else "postgresql-isolated-test",
                "users_created": users_1,
                "master_created": master_1,
                "opening_entries": open_1,
                "boms_created": bom_1["boms_created"],
                "idempotency_verified": True,
            }
    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Isolated Benchmark Test Database Reset & Seed")
    parser.add_argument(
        "--database-url",
        default=os.getenv("BENCHMARK_TEST_DATABASE_URL", "sqlite:///./.benchmark_test_isolated.db"),
        help="Dedicated isolated test DB URL (defaults to BENCHMARK_TEST_DATABASE_URL or local SQLite file).",
    )
    args = parser.parse_args()
    summary = reset_and_seed_benchmark_db(args.database_url)
    print(f"Benchmark reset & seed complete: {summary}")


if __name__ == "__main__":
    main()
