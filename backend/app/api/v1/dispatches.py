from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip, require_permissions
from app.core.database import get_db
from app.core.permissions import Permission
from app.models.user import User
from app.schemas.master_data import PaginatedResponse
from app.schemas.sales import DispatchCreate, DispatchOut
from app.services.sales_service import (
    create_dispatch,
    get_dispatch_or_404,
    list_dispatches,
    to_dispatch_out,
)

router = APIRouter(prefix="/dispatches", tags=["dispatches"])


@router.get("", response_model=PaginatedResponse[DispatchOut])
def get_dispatches(
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_permissions(Permission.DISPATCHES_READ)),
    db: Session = Depends(get_db),
) -> PaginatedResponse[DispatchOut]:
    items, total = list_dispatches(db, search=search, page=page, page_size=page_size)
    return PaginatedResponse(
        items=[to_dispatch_out(d) for d in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=DispatchOut, status_code=status.HTTP_201_CREATED)
def post_create_dispatch(
    payload: DispatchCreate,
    request: Request,
    actor: User = Depends(require_permissions(Permission.DISPATCHES_MANAGE)),
    db: Session = Depends(get_db),
) -> DispatchOut:
    dispatch = create_dispatch(db, payload, actor=actor, ip_address=get_client_ip(request))
    return to_dispatch_out(dispatch)


@router.get("/{dispatch_id}", response_model=DispatchOut)
def get_dispatch_detail(
    dispatch_id: str,
    _: User = Depends(require_permissions(Permission.DISPATCHES_READ)),
    db: Session = Depends(get_db),
) -> DispatchOut:
    return to_dispatch_out(get_dispatch_or_404(db, dispatch_id))
