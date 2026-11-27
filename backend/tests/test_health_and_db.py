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


def test_production_rejects_default_jwt_secret():
    prod_insecure = Settings(environment="production")
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        validate_production_settings(prod_insecure)

    prod_valid = Settings(
        environment="production",
        SECRET_KEY="a-very-strong-production-secret-key-with-at-least-32-chars",
    )
    validate_production_settings(prod_valid)
