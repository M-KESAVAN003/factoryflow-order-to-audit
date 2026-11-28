import pytest

from app.core.config import Settings
from app.core.database import normalize_database_url
from app.main import validate_production_settings


def test_health_endpoint_reports_connected(client):
    for endpoint in ("/health", "/api/v1/health"):
        resp = client.get(endpoint)
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["database"] == "connected"
        assert "password" not in resp.text.lower()


def test_neon_database_url_normalization():
    raw_postgres = "postgres://user:pass@ep-cool-leaf-123.us-east-2.aws.neon.tech/neondb"
    normalized = normalize_database_url(raw_postgres)
    assert normalized.startswith("postgresql+psycopg://")
    assert "sslmode=require" in normalized

    already_ssl = "postgresql://user:pass@ep-cool-leaf-123.neon.tech/neondb?sslmode=require"
    normalized_ssl = normalize_database_url(already_ssl)
    assert normalized_ssl.startswith("postgresql+psycopg://")
    assert normalized_ssl.count("sslmode=require") == 1


def test_production_rejects_default_jwt_secret(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    prod_insecure = Settings(environment="production", _env_file=None)
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        validate_production_settings(prod_insecure)

    prod_valid = Settings(
        environment="production",
        SECRET_KEY="a-very-strong-production-secret-key-with-at-least-32-chars",
        _env_file=None,
    )
    validate_production_settings(prod_valid)


def test_postgresql_for_update_of_avoids_outer_join_locks():
    """Ensure FOR UPDATE targets root tables explicitly for joined relationships in PostgreSQL."""
    from sqlalchemy import select
    from sqlalchemy.dialects import postgresql

    from app.models.costing_payment import Payment
    from app.models.inventory import StockBalance
    from app.models.sales import Invoice

    pg = postgresql.dialect()
    cases = [
        (select(StockBalance).with_for_update(of=StockBalance), "FOR UPDATE OF stock_balances"),
        (select(Invoice).with_for_update(of=Invoice), "FOR UPDATE OF invoices"),
        (select(Payment).with_for_update(of=Payment), "FOR UPDATE OF payments"),
    ]
    for stmt, expected_clause in cases:
        sql = str(stmt.compile(dialect=pg))
        assert expected_clause in sql
        assert not sql.rstrip().endswith("FOR UPDATE")
