from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_permissions
from app.core.database import get_db
from app.core.permissions import Permission
from app.models.user import User
from app.schemas.dashboard import RoleDashboardResponse
from app.schemas.reports import DomainDashboardOut, OwnerDashboardOut
from app.services.dashboard_service import build_role_dashboard
from app.services.owner_dashboard_service import (
    build_domain_dashboard,
    build_owner_dashboard,
    resolve_date_range,
)

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=RoleDashboardResponse)
def get_role_dashboard(
    current_user: User = Depends(require_permissions(Permission.DASHBOARD_VIEW)),
    db: Session = Depends(get_db),
) -> RoleDashboardResponse:
    """Return live DB-backed metrics, capabilities, and recent activity for the active role."""
    return build_role_dashboard(db, current_user)


@router.get("/workspaces/orders")
def read_orders_workspace(
    current_user: User = Depends(require_permissions(Permission.ORDERS_READ)),
) -> dict[str, object]:
    """Verify orders:read capability for Order & Production workflows."""
    return {
        "workspace": "orders",
        "role": current_user.role.value,
        "can_manage": current_user.role.value in {"admin", "order_manager"},
        "phase": "phase_1_rbac_verified",
    }


@router.get("/workspaces/production")
def read_production_workspace(
    current_user: User = Depends(require_permissions(Permission.PRODUCTION_READ)),
) -> dict[str, object]:
    """Verify production:read capability for Shop Floor execution workflows."""
    return {
        "workspace": "production",
        "role": current_user.role.value,
        "can_manage": current_user.role.value in {"admin", "floor_supervisor"},
        "phase": "phase_1_rbac_verified",
    }


@router.get("/workspaces/qa")
def read_qa_workspace(
    current_user: User = Depends(require_permissions(Permission.QA_READ)),
) -> dict[str, object]:
    """Verify qa:read capability for Quality Assurance workflows."""
    return {
        "workspace": "qa",
        "role": current_user.role.value,
        "can_manage": current_user.role.value in {"admin", "qa_inspector"},
        "phase": "phase_1_rbac_verified",
    }


@router.get("/dashboard/owner", response_model=OwnerDashboardOut)
def get_owner_dashboard(
    preset: str = Query(default="last_30_days"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    month: str | None = Query(default=None),
    financial_year: str | None = Query(default=None),
    _: User = Depends(require_permissions(Permission.OWNER_DASHBOARD_VIEW)),
    db: Session = Depends(get_db),
) -> OwnerDashboardOut:
    return build_owner_dashboard(
        db,
        preset=preset,
        date_from=date_from,
        date_to=date_to,
        month=month,
        financial_year=financial_year,
    )


@router.get("/dashboard/sales", response_model=DomainDashboardOut)
def get_sales_domain_dashboard(
    preset: str = Query(default="last_30_days"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    month: str | None = Query(default=None),
    financial_year: str | None = Query(default=None),
    actor: User = Depends(require_permissions(Permission.SALES_ORDERS_READ)),
    db: Session = Depends(get_db),
) -> DomainDashboardOut:
    dr = resolve_date_range(
        preset=preset,
        date_from=date_from,
        date_to=date_to,
        month=month,
        financial_year=financial_year,
    )
    return build_domain_dashboard(db, domain="sales", actor=actor, dr=dr)


@router.get("/dashboard/production", response_model=DomainDashboardOut)
def get_production_domain_dashboard(
    preset: str = Query(default="last_30_days"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    month: str | None = Query(default=None),
    financial_year: str | None = Query(default=None),
    actor: User = Depends(require_permissions(Permission.PRODUCTION_RUNS_READ)),
    db: Session = Depends(get_db),
) -> DomainDashboardOut:
    dr = resolve_date_range(
        preset=preset,
        date_from=date_from,
        date_to=date_to,
        month=month,
        financial_year=financial_year,
    )
    return build_domain_dashboard(db, domain="production", actor=actor, dr=dr)


@router.get("/dashboard/inventory", response_model=DomainDashboardOut)
def get_inventory_domain_dashboard(
    preset: str = Query(default="last_30_days"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    month: str | None = Query(default=None),
    financial_year: str | None = Query(default=None),
    actor: User = Depends(require_permissions(Permission.INVENTORY_READ)),
    db: Session = Depends(get_db),
) -> DomainDashboardOut:
    dr = resolve_date_range(
        preset=preset,
        date_from=date_from,
        date_to=date_to,
        month=month,
        financial_year=financial_year,
    )
    return build_domain_dashboard(db, domain="inventory", actor=actor, dr=dr)


@router.get("/dashboard/finance", response_model=DomainDashboardOut)
def get_finance_domain_dashboard(
    preset: str = Query(default="last_30_days"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    month: str | None = Query(default=None),
    financial_year: str | None = Query(default=None),
    actor: User = Depends(require_permissions(Permission.RECEIVABLES_READ)),
    db: Session = Depends(get_db),
) -> DomainDashboardOut:
    dr = resolve_date_range(
        preset=preset,
        date_from=date_from,
        date_to=date_to,
        month=month,
        financial_year=financial_year,
    )
    return build_domain_dashboard(db, domain="finance", actor=actor, dr=dr)
