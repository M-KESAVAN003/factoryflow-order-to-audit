from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip, require_permissions
from app.core.database import get_db
from app.core.permissions import Permission, Role
from app.models.user import User
from app.schemas.master_data import (
    PaginatedResponse,
    ProductCreate,
    ProductOut,
    ProductUpdate,
)
from app.services.product_service import (
    create_product,
    deactivate_or_delete_product,
    get_product_or_404,
    list_products,
    to_product_out,
    update_product,
)

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=PaginatedResponse[ProductOut])
def get_products(
    search: str | None = Query(default=None),
    category: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    sort_by: str = Query(default="name", pattern="^(name|sku|selling_price|created_at)$"),
    sort_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_permissions(Permission.PRODUCTS_READ)),
    db: Session = Depends(get_db),
) -> PaginatedResponse[ProductOut]:
    """List finished-good products (order_manager sees active products only)."""
    items, total = list_products(
        db,
        search=search,
        category=category,
        is_active=is_active,
        only_active=(current_user.role == Role.ORDER_MANAGER),
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[to_product_out(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def post_product(
    payload: ProductCreate,
    request: Request,
    actor: User = Depends(require_permissions(Permission.PRODUCTS_MANAGE)),
    db: Session = Depends(get_db),
) -> ProductOut:
    """Create a finished product and link it to a FINISHED_GOOD stock item."""
    product = create_product(db, payload, actor=actor, ip_address=get_client_ip(request))
    return to_product_out(product)


@router.get("/{product_id}", response_model=ProductOut)
def get_product(
    product_id: str,
    _: User = Depends(require_permissions(Permission.PRODUCTS_READ)),
    db: Session = Depends(get_db),
) -> ProductOut:
    return to_product_out(get_product_or_404(db, product_id))


@router.put("/{product_id}", response_model=ProductOut)
def put_product(
    product_id: str,
    payload: ProductUpdate,
    request: Request,
    actor: User = Depends(require_permissions(Permission.PRODUCTS_MANAGE)),
    db: Session = Depends(get_db),
) -> ProductOut:
    product = update_product(
        db, product_id, payload, actor=actor, ip_address=get_client_ip(request)
    )
    return to_product_out(product)


@router.delete("/{product_id}")
def delete_product(
    product_id: str,
    request: Request,
    actor: User = Depends(require_permissions(Permission.PRODUCTS_MANAGE)),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    return deactivate_or_delete_product(
        db, product_id, actor=actor, ip_address=get_client_ip(request)
    )
