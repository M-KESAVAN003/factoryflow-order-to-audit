from datetime import date

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip, require_permissions
from app.core.database import get_db
from app.core.permissions import Permission
from app.models.purchase import PurchaseStatus
from app.models.user import User
from app.schemas.inventory_purchase import (
    PurchaseCancelRequest,
    PurchaseCreate,
    PurchaseOut,
    PurchaseUpdate,
)
from app.schemas.master_data import PaginatedResponse
from app.services.purchase_service import (
    cancel_purchase,
    create_purchase,
    export_purchases_csv,
    export_purchases_excel_tsv,
    export_purchases_pdf,
    get_purchase_or_404,
    list_purchases,
    post_purchase,
    to_purchase_out,
    update_purchase,
)

router = APIRouter(prefix="/purchases", tags=["purchases"])


@router.get("", response_model=PaginatedResponse[PurchaseOut])
def get_purchases(
    search: str | None = Query(default=None),
    supplier_id: str | None = Query(default=None),
    status_filter: PurchaseStatus | None = Query(default=None, alias="status"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    sort_by: str = Query(
        default="purchase_date", pattern="^(purchase_date|reference_number|total_amount|created_at)$"
    ),
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_permissions(Permission.PURCHASES_READ)),
    db: Session = Depends(get_db),
) -> PaginatedResponse[PurchaseOut]:
    items, total = list_purchases(
        db,
        search=search,
        supplier_id=supplier_id,
        status_filter=status_filter,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[to_purchase_out(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/export")
def export_purchase_register(
    format: str = Query(default="csv", pattern="^(csv|excel|pdf)$"),
    search: str | None = Query(default=None),
    supplier_id: str | None = Query(default=None),
    status_filter: PurchaseStatus | None = Query(default=None, alias="status"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    _: User = Depends(require_permissions(Permission.PURCHASES_READ)),
    db: Session = Depends(get_db),
) -> Response:
    """Export purchase register in CSV, Excel-compatible TSV, or PDF format."""
    items, _ = list_purchases(
        db,
        search=search,
        supplier_id=supplier_id,
        status_filter=status_filter,
        date_from=date_from,
        date_to=date_to,
        page=1,
        page_size=500,
    )
    if format == "pdf":
        return Response(
            content=export_purchases_pdf(items),
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="purchases-register.pdf"'},
        )
    if format == "excel":
        return Response(
            content=export_purchases_excel_tsv(items),
            media_type="application/vnd.ms-excel",
            headers={"Content-Disposition": 'attachment; filename="purchases-register.xls"'},
        )
    return Response(
        content=export_purchases_csv(items),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="purchases-register.csv"'},
    )


@router.post("", response_model=PurchaseOut, status_code=status.HTTP_201_CREATED)
def post_create_purchase(
    payload: PurchaseCreate,
    request: Request,
    actor: User = Depends(require_permissions(Permission.PURCHASES_MANAGE)),
    db: Session = Depends(get_db),
) -> PurchaseOut:
    purchase = create_purchase(db, payload, actor=actor, ip_address=get_client_ip(request))
    return to_purchase_out(purchase)


@router.get("/{purchase_id}", response_model=PurchaseOut)
def get_purchase_detail(
    purchase_id: str,
    _: User = Depends(require_permissions(Permission.PURCHASES_READ)),
    db: Session = Depends(get_db),
) -> PurchaseOut:
    return to_purchase_out(get_purchase_or_404(db, purchase_id))


@router.put("/{purchase_id}", response_model=PurchaseOut)
def put_update_purchase(
    purchase_id: str,
    payload: PurchaseUpdate,
    request: Request,
    actor: User = Depends(require_permissions(Permission.PURCHASES_MANAGE)),
    db: Session = Depends(get_db),
) -> PurchaseOut:
    purchase = update_purchase(
        db, purchase_id, payload, actor=actor, ip_address=get_client_ip(request)
    )
    return to_purchase_out(purchase)


@router.post("/{purchase_id}/post", response_model=PurchaseOut)
def post_purchase_receipt(
    purchase_id: str,
    request: Request,
    actor: User = Depends(require_permissions(Permission.PURCHASES_MANAGE)),
    db: Session = Depends(get_db),
) -> PurchaseOut:
    purchase = post_purchase(db, purchase_id, actor=actor, ip_address=get_client_ip(request))
    return to_purchase_out(purchase)


@router.post("/{purchase_id}/cancel", response_model=PurchaseOut)
def post_cancel_purchase(
    purchase_id: str,
    payload: PurchaseCancelRequest,
    request: Request,
    actor: User = Depends(require_permissions(Permission.PURCHASES_MANAGE)),
    db: Session = Depends(get_db),
) -> PurchaseOut:
    purchase = cancel_purchase(
        db,
        purchase_id,
        reason=payload.reason,
        actor=actor,
        ip_address=get_client_ip(request),
    )
    return to_purchase_out(purchase)
