from functools import lru_cache
from typing import List
from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "FactoryFlow API"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"

    # Neon / Managed PostgreSQL connection string (must be configured in .env / environment)
    database_url: str = Field(
        default="postgresql://neondb_owner:change_me@ep-example.neon.tech/neondb?sslmode=require"
    )
    db_pool_size: int = 5
    db_max_overflow: int = 5
    db_pool_recycle: int = 300
    db_echo: bool = False

    # JWT Authentication (accepts SECRET_KEY on Render or JWT_SECRET_KEY locally)
    jwt_secret_key: str = Field(
        default="dev-insecure-change-me-in-production-min-32-bytes",
        validation_alias=AliasChoices("SECRET_KEY", "JWT_SECRET_KEY"),
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # CORS
    cors_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    # Factory GST & Dispatch Configuration (Phase 5)
    factory_name: str = "FactoryFlow Foods Pvt Ltd"
    factory_address: str = "Plot 42, SIPCOT Food Processing Park, Chennai, Tamil Nadu - 600058"
    factory_gstin: str = "33AAACF1234F1Z5"
    factory_state: str = "Tamil Nadu"
    factory_state_code: str = "33"
    default_payment_term_days: int = 30

    # Optional non-production demo seed bootstrap
    seed_default_users: bool = Field(
        default=False,
        validation_alias=AliasChoices("DEMO_SEED_ENABLED", "SEED_DEFAULT_USERS"),
    )
    seed_default_password: str = Field(
        default="FactoryFlow!2026",
        validation_alias=AliasChoices("DEMO_SEED_PASSWORD", "SEED_DEFAULT_PASSWORD"),
    )

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() in {"production", "prod"}

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> List[str]:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                import json

                return list(json.loads(stripped))
            return [origin.strip() for origin in stripped.split(",") if origin.strip()]
        if isinstance(value, list):
            return [str(v) for v in value]
        return ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
