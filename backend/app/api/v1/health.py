from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.database import check_database_connection, get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)) -> JSONResponse:
    """Report API and database readiness."""
    db_ok = check_database_connection(db)
    payload = {
        "status": "ok" if db_ok else "degraded",
        "service": "factoryflow-api",
        "database": "connected" if db_ok else "unreachable",
    }
    code = status.HTTP_200_OK if db_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(content=payload, status_code=code)
