from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip, require_permissions
from app.core.database import get_db
from app.core.permissions import Permission, Role
from app.models.production import ProductionStatus
from app.models.user import User
from app.schemas.bom_production import (
    ProductionCancelRequest,
    ProductionConsumeRequest,
    ProductionDashboardOut,
    ProductionOutputInput,
    ProductionRunCreate,
    ProductionRunOut,
    ProductionRunUpdate,
    ProductionWastageInput,
    RunVarianceReportOut,
    VarianceSummaryOut,
)
from app.schemas.costing_payment import (
    ProductionExpenseCreate,
    ProductionExpenseOut,
    ProductionExpenseUpdate,
)
from app.schemas.master_data import PaginatedResponse
from app.services.costing_service import (
    create_run_expense,
    list_run_expenses,
    post_run_expense,
    reverse_run_expense,
    to_expense_out,
    update_run_expense,
)
from app.services.production_service import (
    build_production_dashboard,
    build_run_variance_report,
    build_variance_summary,
    cancel_production_run,
    complete_production_run,
    create_production_run,
    get_production_run_or_404,
    list_production_runs,
    post_production_run,
    record_material_consumption,
    record_production_output,
    record_wastage,
    start_production_run,
    to_production_run_out,
    update_production_run,
)

router = APIRouter(prefix="/production", tags=["production"])


@router.get("/dashboard", response_model=ProductionDashboardOut)
def get_production_dashboard(
    _: User = Depends(require_permissions(Permission.PRODUCTION_RUNS_READ)),
    db: Session = Depends(get_db),
) -> ProductionDashboardOut:
    return build_production_dashboard(db)


@router.get("/variance/summary", response_model=VarianceSummaryOut)
def get_variance_summary(
    _: User = Depends(require_permissions(Permission.PRODUCTION_RUNS_READ)),
    db: Session = Depends(get_db),
) -> VarianceSummaryOut:
    return build_variance_summary(db)


@router.get("", response_model=PaginatedResponse[ProductionRunOut])
def get_production_runs(
    search: str | None = Query(default=None),
    product_id: str | None = Query(default=None),
    status_filter: ProductionStatus | None = Query(default=None, alias="status"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_permissions(Permission.PRODUCTION_RUNS_READ)),
    db: Session = Depends(get_db),
) -> PaginatedResponse[ProductionRunOut]:
    items, total = list_production_runs(
        db,
        search=search,
        product_id=product_id,
        status_filter=status_filter,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[to_production_run_out(db, r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=ProductionRunOut, status_code=status.HTTP_201_CREATED)
def post_create_production_run(
    payload: ProductionRunCreate,
    request: Request,
    actor: User = Depends(require_permissions(Permission.PRODUCTION_RUNS_MANAGE)),
    db: Session = Depends(get_db),
) -> ProductionRunOut:
    run = create_production_run(
        db, payload, actor=actor, ip_address=get_client_ip(request)
    )
    return to_production_run_out(db, run)


@router.get("/{run_id}", response_model=ProductionRunOut)
def get_production_run_detail(
    run_id: str,
    _: User = Depends(require_permissions(Permission.PRODUCTION_RUNS_READ)),
    db: Session = Depends(get_db),
) -> ProductionRunOut:
    return to_production_run_out(db, get_production_run_or_404(db, run_id))


@router.put("/{run_id}", response_model=ProductionRunOut)
def put_update_production_run(
    run_id: str,
    payload: ProductionRunUpdate,
    request: Request,
    actor: User = Depends(require_permissions(Permission.PRODUCTION_RUNS_MANAGE)),
    db: Session = Depends(get_db),
) -> ProductionRunOut:
    run = update_production_run(
        db, run_id, payload, actor=actor, ip_address=get_client_ip(request)
    )
    return to_production_run_out(db, run)


@router.post("/{run_id}/start", response_model=ProductionRunOut)
def post_start_production_run(
    run_id: str,
    request: Request,
    actor: User = Depends(require_permissions(Permission.PRODUCTION_RUNS_MANAGE)),
    db: Session = Depends(get_db),
) -> ProductionRunOut:
    run = start_production_run(db, run_id, actor=actor, ip_address=get_client_ip(request))
    return to_production_run_out(db, run)


@router.post("/{run_id}/consume", response_model=ProductionRunOut)
def post_record_consumption(
    run_id: str,
    payload: ProductionConsumeRequest,
    request: Request,
    actor: User = Depends(require_permissions(Permission.PRODUCTION_RUNS_MANAGE)),
    db: Session = Depends(get_db),
) -> ProductionRunOut:
    run = record_material_consumption(
        db, run_id, payload, actor=actor, ip_address=get_client_ip(request)
    )
    return to_production_run_out(db, run)


@router.post("/{run_id}/output", response_model=ProductionRunOut)
def post_record_output(
    run_id: str,
    payload: ProductionOutputInput,
    request: Request,
    actor: User = Depends(require_permissions(Permission.PRODUCTION_RUNS_MANAGE)),
    db: Session = Depends(get_db),
) -> ProductionRunOut:
    run = record_production_output(
        db, run_id, payload, actor=actor, ip_address=get_client_ip(request)
    )
    return to_production_run_out(db, run)


@router.post("/{run_id}/wastage", response_model=ProductionRunOut)
def post_record_wastage(
    run_id: str,
    payload: ProductionWastageInput,
    request: Request,
    actor: User = Depends(require_permissions(Permission.PRODUCTION_RUNS_MANAGE)),
    db: Session = Depends(get_db),
) -> ProductionRunOut:
    run = record_wastage(
        db, run_id, payload, actor=actor, ip_address=get_client_ip(request)
    )
    return to_production_run_out(db, run)


@router.post("/{run_id}/complete", response_model=ProductionRunOut)
def post_complete_production_run(
    run_id: str,
    request: Request,
    actor: User = Depends(require_permissions(Permission.PRODUCTION_RUNS_MANAGE)),
    db: Session = Depends(get_db),
) -> ProductionRunOut:
    run = complete_production_run(db, run_id, actor=actor, ip_address=get_client_ip(request))
    return to_production_run_out(db, run)


@router.post("/{run_id}/post", response_model=ProductionRunOut)
def post_production_run_to_ledger(
    run_id: str,
    request: Request,
    actor: User = Depends(require_permissions(Permission.PRODUCTION_RUNS_MANAGE)),
    db: Session = Depends(get_db),
) -> ProductionRunOut:
    run = post_production_run(db, run_id, actor=actor, ip_address=get_client_ip(request))
    return to_production_run_out(db, run)


@router.post("/{run_id}/cancel", response_model=ProductionRunOut)
def post_cancel_production_run(
    run_id: str,
    payload: ProductionCancelRequest,
    request: Request,
    actor: User = Depends(require_permissions(Permission.PRODUCTION_RUNS_MANAGE)),
    db: Session = Depends(get_db),
) -> ProductionRunOut:
    existing = get_production_run_or_404(db, run_id)
    if existing.status == ProductionStatus.POSTED and actor.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can approve posted production reversal corrections.",
        )
    run = cancel_production_run(
        db, run_id, reason=payload.reason, actor=actor, ip_address=get_client_ip(request)
    )
    return to_production_run_out(db, run)


@router.get("/{run_id}/variance", response_model=RunVarianceReportOut)
def get_production_run_variance(
    run_id: str,
    _: User = Depends(require_permissions(Permission.PRODUCTION_RUNS_READ)),
    db: Session = Depends(get_db),
) -> RunVarianceReportOut:
    return build_run_variance_report(db, run_id)


@router.get("/{run_id}/expenses", response_model=list[ProductionExpenseOut])
def get_production_run_expenses(
    run_id: str,
    _: User = Depends(require_permissions(Permission.COSTING_READ)),
    db: Session = Depends(get_db),
) -> list[ProductionExpenseOut]:
    return [to_expense_out(e) for e in list_run_expenses(db, run_id)]


@router.post("/{run_id}/expenses", response_model=ProductionExpenseOut, status_code=status.HTTP_201_CREATED)
def post_add_production_run_expense(
    run_id: str,
    payload: ProductionExpenseCreate,
    request: Request,
    actor: User = Depends(require_permissions(Permission.EXPENSES_MANAGE)),
    db: Session = Depends(get_db),
) -> ProductionExpenseOut:
    exp = create_run_expense(db, run_id, payload, actor=actor, ip_address=get_client_ip(request))
    return to_expense_out(exp)


@router.put("/{run_id}/expenses/{expense_id}", response_model=ProductionExpenseOut)
def put_update_production_run_expense(
    run_id: str,
    expense_id: str,
    payload: ProductionExpenseUpdate,
    request: Request,
    actor: User = Depends(require_permissions(Permission.EXPENSES_MANAGE)),
    db: Session = Depends(get_db),
) -> ProductionExpenseOut:
    exp = update_run_expense(
        db, run_id, expense_id, payload, actor=actor, ip_address=get_client_ip(request)
    )
    return to_expense_out(exp)


@router.post("/{run_id}/expenses/{expense_id}/post", response_model=ProductionExpenseOut)
def post_finalize_production_run_expense(
    run_id: str,
    expense_id: str,
    request: Request,
    actor: User = Depends(require_permissions(Permission.EXPENSES_MANAGE)),
    db: Session = Depends(get_db),
) -> ProductionExpenseOut:
    exp = post_run_expense(
        db, run_id, expense_id, actor=actor, ip_address=get_client_ip(request)
    )
    return to_expense_out(exp)


@router.post("/{run_id}/expenses/{expense_id}/reverse", response_model=ProductionExpenseOut)
def post_reverse_production_run_expense(
    run_id: str,
    expense_id: str,
    request: Request,
    actor: User = Depends(require_permissions(Permission.EXPENSES_MANAGE)),
    db: Session = Depends(get_db),
) -> ProductionExpenseOut:
    rev = reverse_run_expense(
        db, run_id, expense_id, actor=actor, ip_address=get_client_ip(request)
    )
    return to_expense_out(rev)
