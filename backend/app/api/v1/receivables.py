from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_permissions
from app.core.database import get_db
from app.core.permissions import Permission
from app.models.user import User
from app.schemas.costing_payment import ReceivablesAgeingReportOut, ReceivablesReportOut
from app.services.payment_service import (
    build_receivables_ageing_report,
    build_receivables_report,
)

router = APIRouter(prefix="/receivables", tags=["receivables"])


@router.get("", response_model=ReceivablesReportOut)
def get_receivables(
    customer_id: str | None = Query(default=None),
    as_of_date: date | None = Query(default=None),
    _: User = Depends(require_permissions(Permission.RECEIVABLES_READ)),
    db: Session = Depends(get_db),
) -> ReceivablesReportOut:
    return build_receivables_report(db, customer_id=customer_id, as_of=as_of_date)


@router.get("/ageing", response_model=ReceivablesAgeingReportOut)
def get_receivables_ageing(
    customer_id: str | None = Query(default=None),
    as_of_date: date | None = Query(default=None),
    _: User = Depends(require_permissions(Permission.RECEIVABLES_READ)),
    db: Session = Depends(get_db),
) -> ReceivablesAgeingReportOut:
    return build_receivables_ageing_report(db, customer_id=customer_id, as_of=as_of_date)


@router.get("/customers/{customer_id}", response_model=ReceivablesReportOut)
def get_customer_receivables(
    customer_id: str,
    as_of_date: date | None = Query(default=None),
    _: User = Depends(require_permissions(Permission.RECEIVABLES_READ)),
    db: Session = Depends(get_db),
) -> ReceivablesReportOut:
    return build_receivables_report(db, customer_id=customer_id, as_of=as_of_date)
