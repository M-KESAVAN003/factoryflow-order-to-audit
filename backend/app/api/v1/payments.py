from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip, require_permissions
from app.core.database import get_db
from app.core.permissions import Permission
from app.models.user import User
from app.schemas.costing_payment import (
    PaymentAllocateRequest,
    PaymentCreate,
    PaymentOut,
)
from app.schemas.master_data import PaginatedResponse
from app.services.payment_service import (
    allocate_payment,
    create_payment,
    get_payment_or_404,
    list_payments,
    to_payment_out,
)

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("", response_model=PaginatedResponse[PaymentOut])
def get_payments(
    search: str | None = Query(default=None),
    customer_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_permissions(Permission.PAYMENTS_READ)),
    db: Session = Depends(get_db),
) -> PaginatedResponse[PaymentOut]:
    items, total = list_payments(
        db, search=search, customer_id=customer_id, page=page, page_size=page_size
    )
    return PaginatedResponse(
        items=[to_payment_out(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def post_create_payment(
    payload: PaymentCreate,
    request: Request,
    actor: User = Depends(require_permissions(Permission.PAYMENTS_MANAGE)),
    db: Session = Depends(get_db),
) -> PaymentOut:
    payment = create_payment(db, payload, actor=actor, ip_address=get_client_ip(request))
    return to_payment_out(payment)


@router.get("/{payment_id}", response_model=PaymentOut)
def get_payment_detail(
    payment_id: str,
    _: User = Depends(require_permissions(Permission.PAYMENTS_READ)),
    db: Session = Depends(get_db),
) -> PaymentOut:
    return to_payment_out(get_payment_or_404(db, payment_id))


@router.post("/{payment_id}/allocate", response_model=PaymentOut)
def post_allocate_payment(
    payment_id: str,
    payload: PaymentAllocateRequest,
    request: Request,
    actor: User = Depends(require_permissions(Permission.PAYMENTS_MANAGE)),
    db: Session = Depends(get_db),
) -> PaymentOut:
    payment = allocate_payment(
        db, payment_id, payload, actor=actor, ip_address=get_client_ip(request)
    )
    return to_payment_out(payment)
