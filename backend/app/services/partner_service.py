from typing import List, Tuple

from fastapi import HTTPException, status
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from app.models.customer import Customer, CustomerType
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.master_data import (
    CustomerCreate,
    CustomerOut,
    CustomerUpdate,
    SupplierCreate,
    SupplierUpdate,
)
from app.services.audit_service import record_audit_event


def to_customer_out(customer: Customer) -> CustomerOut:
    return CustomerOut(
        id=customer.id,
        name=customer.name,
        customer_type=customer.customer_type,
        gstin=customer.gstin,
        phone=customer.phone,
        address=customer.address,
        city=customer.city,
        state=customer.state,
        state_code=customer.state_code,
        assigned_salesman_id=customer.assigned_salesman_id,
        assigned_salesman_name=(
            customer.assigned_salesman.full_name if customer.assigned_salesman else None
        ),
        credit_limit=customer.credit_limit,
        is_active=customer.is_active,
        created_at=customer.created_at,
        updated_at=customer.updated_at,
    )


def list_suppliers(
    db: Session,
    *,
    search: str | None = None,
    state: str | None = None,
    is_active: bool | None = None,
    sort_by: str = "name",
    sort_dir: str = "asc",
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Supplier], int]:
    filters = []
    if search:
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                Supplier.name.ilike(term),
                Supplier.gstin.ilike(term),
                Supplier.phone.ilike(term),
            )
        )
    if state:
        filters.append(func.lower(Supplier.state) == state.strip().lower())
    if is_active is not None:
        filters.append(Supplier.is_active.is_(is_active))

    total = int(db.scalar(select(func.count(Supplier.id)).where(*filters)) or 0)
    col = getattr(Supplier, sort_by, Supplier.name)
    order_fn = desc if sort_dir == "desc" else asc
    stmt = (
        select(Supplier)
        .where(*filters)
        .order_by(order_fn(col))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(db.scalars(stmt).all()), total


def create_supplier(
    db: Session,
    payload: SupplierCreate,
    *,
    actor: User | None = None,
    ip_address: str | None = None,
) -> Supplier:
    if db.scalar(select(Supplier).where(Supplier.gstin == payload.gstin)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Supplier with GSTIN '{payload.gstin}' already exists.",
        )

    supplier = Supplier(
        name=payload.name.strip(),
        gstin=payload.gstin,
        phone=payload.phone.strip(),
        email=str(payload.email).lower() if payload.email else None,
        address=payload.address.strip(),
        state=payload.state.strip(),
        state_code=payload.state_code.strip(),
        is_active=payload.is_active,
    )
    db.add(supplier)
    db.flush()

    record_audit_event(
        db,
        actor_id=actor.id if actor else None,
        actor_email=actor.email if actor else "system@factoryflow.io",
        actor_role=actor.role.value if actor else "system",
        action="master.supplier_created",
        resource_type="supplier",
        resource_id=supplier.id,
        details=f"Created supplier {supplier.name} ({supplier.gstin})",
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(supplier)
    return supplier


def update_supplier(
    db: Session,
    supplier_id: str,
    payload: SupplierUpdate,
    *,
    actor: User,
    ip_address: str | None = None,
) -> Supplier:
    supplier = db.get(Supplier, supplier_id)
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found.")

    if payload.gstin is not None:
        conflict = db.scalar(
            select(Supplier).where(Supplier.gstin == payload.gstin, Supplier.id != supplier.id)
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Supplier with GSTIN '{payload.gstin}' already exists.",
            )
        supplier.gstin = payload.gstin

    if payload.name is not None:
        supplier.name = payload.name.strip()
    if payload.phone is not None:
        supplier.phone = payload.phone.strip()
    if payload.email is not None:
        supplier.email = str(payload.email).lower()
    if payload.address is not None:
        supplier.address = payload.address.strip()
    if payload.state is not None:
        supplier.state = payload.state.strip()
    if payload.state_code is not None:
        supplier.state_code = payload.state_code.strip()
    if payload.is_active is not None:
        supplier.is_active = payload.is_active

    record_audit_event(
        db,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role.value,
        action="master.supplier_updated",
        resource_type="supplier",
        resource_id=supplier.id,
        details=f"Updated supplier {supplier.name}",
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(supplier)
    return supplier


def list_customers(
    db: Session,
    *,
    search: str | None = None,
    customer_type: CustomerType | None = None,
    state: str | None = None,
    is_active: bool | None = None,
    assigned_salesman_id: str | None = None,
    sort_by: str = "name",
    sort_dir: str = "asc",
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[Customer], int]:
    filters = []
    if assigned_salesman_id is not None:
        filters.append(Customer.assigned_salesman_id == assigned_salesman_id)
    if search:
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                Customer.name.ilike(term),
                Customer.gstin.ilike(term),
                Customer.city.ilike(term),
            )
        )
    if customer_type is not None:
        filters.append(Customer.customer_type == customer_type)
    if state:
        filters.append(func.lower(Customer.state) == state.strip().lower())
    if is_active is not None:
        filters.append(Customer.is_active.is_(is_active))

    total = int(db.scalar(select(func.count(Customer.id)).where(*filters)) or 0)
    col = getattr(Customer, sort_by, Customer.name)
    order_fn = desc if sort_dir == "desc" else asc
    stmt = (
        select(Customer)
        .where(*filters)
        .order_by(order_fn(col))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(db.scalars(stmt).all()), total


def create_customer(
    db: Session,
    payload: CustomerCreate,
    *,
    actor: User | None = None,
    ip_address: str | None = None,
) -> Customer:
    if db.scalar(select(Customer).where(Customer.gstin == payload.gstin)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Customer with GSTIN '{payload.gstin}' already exists.",
        )

    if payload.assigned_salesman_id is not None:
        if not db.get(User, payload.assigned_salesman_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assigned salesman user not found.",
            )

    customer = Customer(
        name=payload.name.strip(),
        customer_type=payload.customer_type,
        gstin=payload.gstin,
        phone=payload.phone.strip(),
        address=payload.address.strip(),
        city=payload.city.strip(),
        state=payload.state.strip(),
        state_code=payload.state_code.strip(),
        assigned_salesman_id=payload.assigned_salesman_id,
        credit_limit=payload.credit_limit,
        is_active=payload.is_active,
    )
    db.add(customer)
    db.flush()

    record_audit_event(
        db,
        actor_id=actor.id if actor else None,
        actor_email=actor.email if actor else "system@factoryflow.io",
        actor_role=actor.role.value if actor else "system",
        action="master.customer_created",
        resource_type="customer",
        resource_id=customer.id,
        details=f"Created customer {customer.name} ({customer.customer_type.value})",
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(customer)
    return customer


def update_customer(
    db: Session,
    customer_id: str,
    payload: CustomerUpdate,
    *,
    actor: User,
    ip_address: str | None = None,
) -> Customer:
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")

    if payload.gstin is not None:
        conflict = db.scalar(
            select(Customer).where(Customer.gstin == payload.gstin, Customer.id != customer.id)
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Customer with GSTIN '{payload.gstin}' already exists.",
            )
        customer.gstin = payload.gstin

    if payload.assigned_salesman_id is not None:
        if not db.get(User, payload.assigned_salesman_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assigned salesman user not found.",
            )
        customer.assigned_salesman_id = payload.assigned_salesman_id

    if payload.name is not None:
        customer.name = payload.name.strip()
    if payload.customer_type is not None:
        customer.customer_type = payload.customer_type
    if payload.phone is not None:
        customer.phone = payload.phone.strip()
    if payload.address is not None:
        customer.address = payload.address.strip()
    if payload.city is not None:
        customer.city = payload.city.strip()
    if payload.state is not None:
        customer.state = payload.state.strip()
    if payload.state_code is not None:
        customer.state_code = payload.state_code.strip()
    if payload.credit_limit is not None:
        customer.credit_limit = payload.credit_limit
    if payload.is_active is not None:
        customer.is_active = payload.is_active

    record_audit_event(
        db,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role.value,
        action="master.customer_updated",
        resource_type="customer",
        resource_id=customer.id,
        details=f"Updated customer {customer.name}",
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    db.refresh(customer)
    return customer
