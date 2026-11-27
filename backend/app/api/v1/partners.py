from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip, require_permissions
from app.core.database import get_db
from app.core.permissions import Permission, Role
from app.models.customer import Customer, CustomerType
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.costing_payment import CustomerLedgerOut, CustomerStatementOut
from app.services.payment_service import build_customer_ledger, build_customer_statement
from app.schemas.master_data import (
    CustomerCreate,
    CustomerOut,
    CustomerUpdate,
    PaginatedResponse,
    SupplierCreate,
    SupplierOut,
    SupplierUpdate,
)
from app.services.partner_service import (
    create_customer,
    create_supplier,
    list_customers,
    list_suppliers,
    to_customer_out,
    update_customer,
    update_supplier,
)

router = APIRouter(tags=["partners"])


@router.get("/suppliers", response_model=PaginatedResponse[SupplierOut])
def get_suppliers(
    search: str | None = Query(default=None),
    state: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    sort_by: str = Query(default="name", pattern="^(name|gstin|state|created_at)$"),
    sort_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_permissions(Permission.SUPPLIERS_READ)),
    db: Session = Depends(get_db),
) -> PaginatedResponse[SupplierOut]:
    items, total = list_suppliers(
        db,
        search=search,
        state=state,
        is_active=is_active,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[SupplierOut.model_validate(s) for s in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/suppliers", response_model=SupplierOut, status_code=status.HTTP_201_CREATED)
def post_supplier(
    payload: SupplierCreate,
    request: Request,
    actor: User = Depends(require_permissions(Permission.SUPPLIERS_MANAGE)),
    db: Session = Depends(get_db),
) -> SupplierOut:
    supplier = create_supplier(db, payload, actor=actor, ip_address=get_client_ip(request))
    return SupplierOut.model_validate(supplier)


@router.get("/suppliers/{supplier_id}", response_model=SupplierOut)
def get_supplier(
    supplier_id: str,
    _: User = Depends(require_permissions(Permission.SUPPLIERS_READ)),
    db: Session = Depends(get_db),
) -> SupplierOut:
    supplier = db.get(Supplier, supplier_id)
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found.")
    return SupplierOut.model_validate(supplier)


@router.put("/suppliers/{supplier_id}", response_model=SupplierOut)
def put_supplier(
    supplier_id: str,
    payload: SupplierUpdate,
    request: Request,
    actor: User = Depends(require_permissions(Permission.SUPPLIERS_MANAGE)),
    db: Session = Depends(get_db),
) -> SupplierOut:
    supplier = update_supplier(
        db, supplier_id, payload, actor=actor, ip_address=get_client_ip(request)
    )
    return SupplierOut.model_validate(supplier)


@router.get("/customers", response_model=PaginatedResponse[CustomerOut])
def get_customers(
    search: str | None = Query(default=None),
    customer_type: CustomerType | None = Query(default=None),
    state: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    sort_by: str = Query(default="name", pattern="^(name|city|state|credit_limit|created_at)$"),
    sort_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_permissions(Permission.CUSTOMERS_READ)),
    db: Session = Depends(get_db),
) -> PaginatedResponse[CustomerOut]:
    scoped_salesman_id = (
        current_user.id if current_user.role == Role.ORDER_MANAGER else None
    )
    items, total = list_customers(
        db,
        search=search,
        customer_type=customer_type,
        state=state,
        is_active=is_active,
        assigned_salesman_id=scoped_salesman_id,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[to_customer_out(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/customers", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
def post_customer(
    payload: CustomerCreate,
    request: Request,
    actor: User = Depends(require_permissions(Permission.CUSTOMERS_MANAGE)),
    db: Session = Depends(get_db),
) -> CustomerOut:
    customer = create_customer(db, payload, actor=actor, ip_address=get_client_ip(request))
    return to_customer_out(customer)


@router.get("/customers/{customer_id}", response_model=CustomerOut)
def get_customer(
    customer_id: str,
    current_user: User = Depends(require_permissions(Permission.CUSTOMERS_READ)),
    db: Session = Depends(get_db),
) -> CustomerOut:
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")
    if (
        current_user.role == Role.ORDER_MANAGER
        and customer.assigned_salesman_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You may only view customers assigned to your account.",
        )
    return to_customer_out(customer)


@router.put("/customers/{customer_id}", response_model=CustomerOut)
def put_customer(
    customer_id: str,
    payload: CustomerUpdate,
    request: Request,
    actor: User = Depends(require_permissions(Permission.CUSTOMERS_MANAGE)),
    db: Session = Depends(get_db),
) -> CustomerOut:
    customer = update_customer(
        db, customer_id, payload, actor=actor, ip_address=get_client_ip(request)
    )
    return to_customer_out(customer)


@router.get("/customers/{customer_id}/ledger", response_model=CustomerLedgerOut)
def get_customer_ledger(
    customer_id: str,
    _: User = Depends(require_permissions(Permission.RECEIVABLES_READ)),
    db: Session = Depends(get_db),
) -> CustomerLedgerOut:
    return build_customer_ledger(db, customer_id)


@router.get("/customers/{customer_id}/statement", response_model=CustomerStatementOut)
def get_customer_statement(
    customer_id: str,
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    _: User = Depends(require_permissions(Permission.RECEIVABLES_READ)),
    db: Session = Depends(get_db),
) -> CustomerStatementOut:
    return build_customer_statement(db, customer_id, from_date=from_date, to_date=to_date)
