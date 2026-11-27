from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.core.database import Base, normalize_database_url
from app.models import (  # noqa: F401 - register all SQLAlchemy models on Base.metadata
    AuditLog,
    BomHeader,
    BomLine,
    CreditNote,
    Customer,
    Dispatch,
    DispatchItem,
    Invoice,
    InvoiceItem,
    Payment,
    PaymentAllocation,
    Product,
    ProductionExpense,
    ProductionMaterial,
    ProductionOutput,
    ProductionRun,
    ProductionWastage,
    Purchase,
    PurchaseItem,
    SalesOrder,
    SalesOrderItem,
    StockAdjustment,
    StockBalance,
    StockItem,
    StockLedger,
    Supplier,
    Unit,
    UnitConversion,
    User,
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    """Resolve database URL from Alembic override or application settings."""
    configured = config.get_main_option("sqlalchemy.url")
    if configured:
        return normalize_database_url(configured)
    return normalize_database_url(get_settings().database_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=url.startswith("sqlite"),
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    url = get_url()
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = url

    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=connection.dialect.name == "sqlite",
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
