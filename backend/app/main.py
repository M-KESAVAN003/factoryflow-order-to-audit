from contextlib import asynccontextmanager
import logging

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.v1.health import health_check
from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.database import Base, SessionLocal, engine, get_db
from app.models import AuditLog, User  # noqa: F401 - register models with Base metadata
from app.services.user_service import seed_default_users

logger = logging.getLogger("factoryflow")


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def validate_production_settings(settings: Settings) -> None:
    """Fail fast if insecure default secrets or debug flags are left on in production."""
    if settings.is_production and (
        settings.jwt_secret_key.startswith("dev-insecure")
        or len(settings.jwt_secret_key.strip()) < 32
    ):
        raise RuntimeError(
            "SECRET_KEY / JWT_SECRET_KEY must be at least 32 characters in production."
        )
    if (
        settings.is_production
        and settings.seed_default_users
        and (
            settings.seed_default_password.strip()
            in {"", "FactoryFlow!2026", "replace-with-custom-non-default-demo-password"}
            or len(settings.seed_default_password.strip()) < 12
        )
    ):
        raise RuntimeError(
            "DEMO_SEED_ENABLED=true in production requires a unique custom DEMO_SEED_PASSWORD (>=12 chars)."
        )


def init_database() -> None:
    """Create schema tables if missing and optionally seed non-production demo role accounts."""
    Base.metadata.create_all(bind=engine)
    settings = get_settings()
    if settings.seed_default_users:
        with SessionLocal() as db:
            seed_default_users(db, settings.seed_default_password)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    _configure_logging(settings.log_level)
    validate_production_settings(settings)
    logger.info("Starting FactoryFlow API in environment=%s", settings.environment)
    if settings.seed_default_users:
        init_database()
    yield


def create_app() -> FastAPI:
    """Application factory for the FactoryFlow FastAPI service."""
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def safe_unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled API error on %s: %s", request.url.path, exc.__class__.__name__)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error. Contact platform support."},
        )

    @app.get("/health", tags=["health"])
    def root_health_check(db: Session = Depends(get_db)) -> JSONResponse:
        """Render / platform root health probe verifying app & PostgreSQL connectivity."""
        return health_check(db)

    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
