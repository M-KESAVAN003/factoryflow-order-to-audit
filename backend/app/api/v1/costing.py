from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_permissions
from app.core.database import get_db
from app.core.permissions import Permission
from app.models.user import User
from app.schemas.costing_payment import (
    ProductCostSummaryOut,
    ProductionCostDashboardOut,
    RunCostingOut,
)
from app.services.costing_service import (
    build_costing_dashboard,
    build_product_cost_summary,
    build_run_costing,
)

router = APIRouter(prefix="/costing", tags=["costing"])


@router.get("/production", response_model=ProductionCostDashboardOut)
def get_production_cost_dashboard(
    product_id: str | None = Query(default=None),
    _: User = Depends(require_permissions(Permission.COSTING_READ)),
    db: Session = Depends(get_db),
) -> ProductionCostDashboardOut:
    """Return actual weighted-average material + posted overhead costing across production runs."""
    return build_costing_dashboard(db, product_id=product_id)


@router.get("/production/{run_id}", response_model=RunCostingOut)
def get_production_run_costing(
    run_id: str,
    _: User = Depends(require_permissions(Permission.COSTING_READ)),
    db: Session = Depends(get_db),
) -> RunCostingOut:
    return build_run_costing(db, run_id)


@router.get("/products/{product_id}", response_model=ProductCostSummaryOut)
def get_product_costing(
    product_id: str,
    _: User = Depends(require_permissions(Permission.COSTING_READ)),
    db: Session = Depends(get_db),
) -> ProductCostSummaryOut:
    return build_product_cost_summary(db, product_id)
