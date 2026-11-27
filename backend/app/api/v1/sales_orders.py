from collections import defaultdict, deque
from datetime import date
from threading import Lock
import time

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip, require_permissions
from app.core.database import get_db
from app.core.permissions import Permission
from app.models.sales import SalesOrderStatus
from app.models.user import User
from app.schemas.master_data import PaginatedResponse
from app.schemas.sales import (
    SalesOrderApproveRequest,
    SalesOrderCreate,
    SalesOrderOut,
    SalesOrderRejectRequest,
    SalesOrderStockCheckOut,
    SalesOrderSyncRequest,
    SalesOrderSyncResponse,
    SalesOrderUpdate,
    SalesOverviewOut,
)
from app.services.sales_service import (
    approve_sales_order,
    build_sales_overview,
    check_sales_order_stock,
    create_sales_order,
    get_sales_order_or_404,
    list_sales_orders,
    reject_sales_order,
    sync_offline_sales_order,
    to_sales_order_out,
    update_sales_order,
)

router = APIRouter(prefix="/orders", tags=["sales_orders"])

_SYNC_RATE_LOCK = Lock()
_SYNC_BUCKETS: dict[str, deque[float]] = defaultdict(deque)
SYNC_RATE_LIMIT = 120
SYNC_RATE_WINDOW_SEC = 60.0


def reset_sync_rate_limits() -> None:
    with _SYNC_RATE_LOCK:
        _SYNC_BUCKETS.clear()


def _enforce_sync_rate_limit(actor_id: str) -> None:
    now = time.monotonic()
    with _SYNC_RATE_LOCK:
        bucket = _SYNC_BUCKETS[actor_id]
        while bucket and (now - bucket[0]) > SYNC_RATE_WINDOW_SEC:
            bucket.popleft()
        if len(bucket) >= SYNC_RATE_LIMIT:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Sync rate limit exceeded. Please retry shortly.",
            )
        bucket.append(now)


@router.get("/overview", response_model=SalesOverviewOut)
def get_sales_overview(
    actor: User = Depends(require_permissions(Permission.SALES_ORDERS_READ)),
    db: Session = Depends(get_db),
) -> SalesOverviewOut:
    """Salesman / Admin / Auditor overview & customer-wise sales summary."""
    return build_sales_overview(db, actor=actor)


@router.get("", response_model=PaginatedResponse[SalesOrderOut])
def get_sales_orders(
    search: str | None = Query(default=None),
    customer_id: str | None = Query(default=None),
    status_filter: SalesOrderStatus | None = Query(default=None, alias="status"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    actor: User = Depends(require_permissions(Permission.SALES_ORDERS_READ)),
    db: Session = Depends(get_db),
) -> PaginatedResponse[SalesOrderOut]:
    items, total = list_sales_orders(
        db,
        actor=actor,
        search=search,
        customer_id=customer_id,
        status_filter=status_filter,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[to_sales_order_out(db, o) for o in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=SalesOrderOut, status_code=status.HTTP_201_CREATED)
def post_create_sales_order(
    payload: SalesOrderCreate,
    request: Request,
    actor: User = Depends(require_permissions(Permission.SALES_ORDERS_CREATE)),
    db: Session = Depends(get_db),
) -> SalesOrderOut:
    order = create_sales_order(db, payload, actor=actor, ip_address=get_client_ip(request))
    return to_sales_order_out(db, order)


@router.post("/sync", response_model=SalesOrderSyncResponse, status_code=status.HTTP_200_OK)
def post_sync_offline_order(
    payload: SalesOrderSyncRequest,
    request: Request,
    actor: User = Depends(require_permissions(Permission.SALES_ORDERS_CREATE)),
    db: Session = Depends(get_db),
) -> SalesOrderSyncResponse:
    """Idempotently synchronize an offline salesman order into PostgreSQL as SUBMITTED."""
    _enforce_sync_rate_limit(actor.id)
    return sync_offline_sales_order(
        db, payload, actor=actor, ip_address=get_client_ip(request)
    )


@router.get("/{order_id}", response_model=SalesOrderOut)
def get_sales_order_detail(
    order_id: str,
    actor: User = Depends(require_permissions(Permission.SALES_ORDERS_READ)),
    db: Session = Depends(get_db),
) -> SalesOrderOut:
    return to_sales_order_out(db, get_sales_order_or_404(db, order_id, actor=actor))


@router.put("/{order_id}", response_model=SalesOrderOut)
def put_update_sales_order(
    order_id: str,
    payload: SalesOrderUpdate,
    request: Request,
    actor: User = Depends(require_permissions(Permission.SALES_ORDERS_APPROVE)),
    db: Session = Depends(get_db),
) -> SalesOrderOut:
    order = update_sales_order(
        db, order_id, payload, actor=actor, ip_address=get_client_ip(request)
    )
    return to_sales_order_out(db, order)


@router.get("/{order_id}/stock-check", response_model=SalesOrderStockCheckOut)
def get_sales_order_stock_check(
    order_id: str,
    actor: User = Depends(require_permissions(Permission.SALES_ORDERS_READ)),
    db: Session = Depends(get_db),
) -> SalesOrderStockCheckOut:
    return check_sales_order_stock(db, order_id, actor=actor)


@router.post("/{order_id}/approve", response_model=SalesOrderOut)
def post_approve_sales_order(
    order_id: str,
    request: Request,
    payload: SalesOrderApproveRequest | None = None,
    actor: User = Depends(require_permissions(Permission.SALES_ORDERS_APPROVE)),
    db: Session = Depends(get_db),
) -> SalesOrderOut:
    order = approve_sales_order(
        db,
        order_id,
        payload or SalesOrderApproveRequest(),
        actor=actor,
        ip_address=get_client_ip(request),
    )
    return to_sales_order_out(db, order)


@router.post("/{order_id}/reject", response_model=SalesOrderOut)
def post_reject_sales_order(
    order_id: str,
    payload: SalesOrderRejectRequest,
    request: Request,
    actor: User = Depends(require_permissions(Permission.SALES_ORDERS_APPROVE)),
    db: Session = Depends(get_db),
) -> SalesOrderOut:
    order = reject_sales_order(
        db, order_id, payload.reason, actor=actor, ip_address=get_client_ip(request)
    )
    return to_sales_order_out(db, order)
