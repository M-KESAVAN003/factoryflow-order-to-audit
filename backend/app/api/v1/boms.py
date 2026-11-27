from typing import List

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip, require_permissions
from app.core.database import get_db
from app.core.permissions import Permission
from app.models.bom import BomStatus
from app.models.user import User
from app.schemas.bom_production import BomCreate, BomOut, BomUpdate
from app.schemas.master_data import PaginatedResponse
from app.services.bom_service import (
    create_bom,
    get_bom_or_404,
    get_bom_versions,
    list_boms,
    to_bom_out,
    update_bom,
)

router = APIRouter(prefix="/boms", tags=["boms"])


@router.get("", response_model=PaginatedResponse[BomOut])
def get_boms(
    product_id: str | None = Query(default=None),
    status_filter: BomStatus | None = Query(default=None, alias="status"),
    is_active: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_permissions(Permission.BOM_READ)),
    db: Session = Depends(get_db),
) -> PaginatedResponse[BomOut]:
    items, total = list_boms(
        db,
        product_id=product_id,
        status_filter=status_filter,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[to_bom_out(db, b) for b in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=BomOut, status_code=status.HTTP_201_CREATED)
def post_create_bom(
    payload: BomCreate,
    request: Request,
    actor: User = Depends(require_permissions(Permission.BOM_MANAGE)),
    db: Session = Depends(get_db),
) -> BomOut:
    bom = create_bom(db, payload, actor=actor, ip_address=get_client_ip(request))
    return to_bom_out(db, bom)


@router.get("/{bom_id}", response_model=BomOut)
def get_bom_detail(
    bom_id: str,
    _: User = Depends(require_permissions(Permission.BOM_READ)),
    db: Session = Depends(get_db),
) -> BomOut:
    return to_bom_out(db, get_bom_or_404(db, bom_id))


@router.put("/{bom_id}", response_model=BomOut)
def put_update_bom(
    bom_id: str,
    payload: BomUpdate,
    request: Request,
    actor: User = Depends(require_permissions(Permission.BOM_MANAGE)),
    db: Session = Depends(get_db),
) -> BomOut:
    bom = update_bom(
        db, bom_id, payload, actor=actor, ip_address=get_client_ip(request)
    )
    return to_bom_out(db, bom)


@router.get("/{bom_id}/versions", response_model=List[BomOut])
def get_bom_version_history(
    bom_id: str,
    _: User = Depends(require_permissions(Permission.BOM_READ)),
    db: Session = Depends(get_db),
) -> List[BomOut]:
    return [to_bom_out(db, b) for b in get_bom_versions(db, bom_id)]
