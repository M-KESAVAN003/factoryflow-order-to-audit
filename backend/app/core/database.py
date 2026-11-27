from typing import Any, Dict, Generator
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import Settings, get_settings


class Base(DeclarativeBase):
    """Declarative base for all SQLAlchemy models."""


def normalize_database_url(raw_url: str) -> str:
    """Normalize PostgreSQL URLs for SQLAlchemy + psycopg v3 and Neon SSL."""
    url = raw_url.strip()
    if url.startswith("sqlite"):
        return url

    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://") :]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]

    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    host = (parsed.hostname or "").lower()

    # Enforce sslmode=require for Neon and remote PostgreSQL hosts when not set.
    if "sslmode" not in query and ("neon.tech" in host or host not in {"localhost", "127.0.0.1"}):
        query["sslmode"] = ["require"]

    new_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def build_engine(settings: Settings | None = None, database_url: str | None = None) -> Engine:
    """Create a SQLAlchemy engine tuned for Neon serverless PostgreSQL or SQLite tests."""
    cfg = settings or get_settings()
    normalized_url = normalize_database_url(database_url or cfg.database_url)

    kwargs: Dict[str, Any] = {
        "echo": cfg.db_echo,
        "future": True,
    }

    if normalized_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        # Neon scales compute to zero when idle; pool_pre_ping + recycle prevent stale sockets.
        kwargs.update(
            {
                "pool_pre_ping": True,
                "pool_size": cfg.db_pool_size,
                "max_overflow": cfg.db_max_overflow,
                "pool_recycle": cfg.db_pool_recycle,
            }
        )

    return create_engine(normalized_url, **kwargs)


engine = build_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection(db: Session) -> bool:
    """Verify database connectivity with a lightweight query."""
    try:
        db.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
