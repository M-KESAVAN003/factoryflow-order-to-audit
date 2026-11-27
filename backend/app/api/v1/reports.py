from datetime import date

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import require_permissions
from app.core.database import get_db
from app.core.permissions import Permission
from app.models.inventory import MovementType
from app.models.purchase import PurchaseStatus
from app.models.stock_item import StockItemType
from app.models.user import User
from app.schemas.reports import (
    CustomerSalesReportOut,
    GstHsnSummaryReportOut,
    GstOutwardSupplyReportOut,
    PaymentRegisterReportOut,
    ProductSalesReportOut,
    ProductionCostReportOut,
    ProductionRegisterReportOut,
    ProductionVarianceReportOut,
    PurchaseRegisterReportOut,
    ReceivablesAgeingAuditOut,
    ReceivablesReportSummaryOut,
    SalesRegisterReportOut,
    SalesmanPerformanceReportOut,
    StockLedgerReportOut,
    StockSummaryReportOut,
)
from app.services.owner_dashboard_service import resolve_date_range
from app.services.report_export_service import (
    collect_report_table,
    export_report_csv,
    export_report_pdf,
    export_report_xlsx,
)
from app.services.reporting_service import (
    report_gst_hsn_summary,
    report_gst_outward_supplies,
    report_payments_register,
    report_production_costing,
    report_production_register,
    report_production_variance,
    report_purchase_register,
    report_receivables_ageing_audit,
    report_receivables_audit,
    report_sales_by_customer,
    report_sales_by_product,
    report_sales_by_salesman,
    report_sales_register,
    report_stock_ledger,
    report_stock_summary,
)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/sales", response_model=SalesRegisterReportOut)
def get_sales_register_report(
    preset: str = Query(default="last_30_days"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    month: str | None = Query(default=None),
    financial_year: str | None = Query(default=None),
    customer_id: str | None = Query(default=None),
    product_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    _: User = Depends(require_permissions(Permission.REPORTS_VIEW)),
    db: Session = Depends(get_db),
) -> SalesRegisterReportOut:
    dr = resolve_date_range(
        preset=preset, date_from=date_from, date_to=date_to, month=month, financial_year=financial_year
    )
    return report_sales_register(
        db, dr=dr, customer_id=customer_id, product_id=product_id, page=page, page_size=page_size
    )


@router.get("/sales/customers", response_model=CustomerSalesReportOut)
def get_customer_sales_report(
    preset: str = Query(default="last_30_days"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    month: str | None = Query(default=None),
    financial_year: str | None = Query(default=None),
    customer_id: str | None = Query(default=None),
    _: User = Depends(require_permissions(Permission.REPORTS_VIEW)),
    db: Session = Depends(get_db),
) -> CustomerSalesReportOut:
    dr = resolve_date_range(
        preset=preset, date_from=date_from, date_to=date_to, month=month, financial_year=financial_year
    )
    return report_sales_by_customer(db, dr=dr, customer_id=customer_id)


@router.get("/sales/products", response_model=ProductSalesReportOut)
def get_product_sales_report(
    preset: str = Query(default="last_30_days"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    month: str | None = Query(default=None),
    financial_year: str | None = Query(default=None),
    product_id: str | None = Query(default=None),
    _: User = Depends(require_permissions(Permission.REPORTS_VIEW)),
    db: Session = Depends(get_db),
) -> ProductSalesReportOut:
    dr = resolve_date_range(
        preset=preset, date_from=date_from, date_to=date_to, month=month, financial_year=financial_year
    )
    return report_sales_by_product(db, dr=dr, product_id=product_id)


@router.get("/sales/salesmen", response_model=SalesmanPerformanceReportOut)
def get_salesman_sales_report(
    preset: str = Query(default="last_30_days"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    month: str | None = Query(default=None),
    financial_year: str | None = Query(default=None),
    _: User = Depends(require_permissions(Permission.REPORTS_VIEW)),
    db: Session = Depends(get_db),
) -> SalesmanPerformanceReportOut:
    dr = resolve_date_range(
        preset=preset, date_from=date_from, date_to=date_to, month=month, financial_year=financial_year
    )
    return report_sales_by_salesman(db, dr=dr)


@router.get("/gst/outward-supplies", response_model=GstOutwardSupplyReportOut)
def get_gst_outward_supplies(
    preset: str = Query(default="last_30_days"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    month: str | None = Query(default=None),
    financial_year: str | None = Query(default=None),
    _: User = Depends(require_permissions(Permission.REPORTS_VIEW)),
    db: Session = Depends(get_db),
) -> GstOutwardSupplyReportOut:
    dr = resolve_date_range(
        preset=preset, date_from=date_from, date_to=date_to, month=month, financial_year=financial_year
    )
    return report_gst_outward_supplies(db, dr=dr)


@router.get("/gst/hsn-summary", response_model=GstHsnSummaryReportOut)
def get_gst_hsn_summary(
    preset: str = Query(default="last_30_days"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    month: str | None = Query(default=None),
    financial_year: str | None = Query(default=None),
    _: User = Depends(require_permissions(Permission.REPORTS_VIEW)),
    db: Session = Depends(get_db),
) -> GstHsnSummaryReportOut:
    dr = resolve_date_range(
        preset=preset, date_from=date_from, date_to=date_to, month=month, financial_year=financial_year
    )
    return report_gst_hsn_summary(db, dr=dr)


@router.get("/purchases", response_model=PurchaseRegisterReportOut)
def get_purchase_register_report(
    preset: str = Query(default="last_30_days"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    month: str | None = Query(default=None),
    financial_year: str | None = Query(default=None),
    supplier_id: str | None = Query(default=None),
    stock_item_id: str | None = Query(default=None),
    status_filter: PurchaseStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    _: User = Depends(require_permissions(Permission.REPORTS_VIEW)),
    db: Session = Depends(get_db),
) -> PurchaseRegisterReportOut:
    dr = resolve_date_range(
        preset=preset, date_from=date_from, date_to=date_to, month=month, financial_year=financial_year
    )
    return report_purchase_register(
        db,
        dr=dr,
        supplier_id=supplier_id,
        stock_item_id=stock_item_id,
        status_filter=status_filter,
        page=page,
        page_size=page_size,
    )


@router.get("/stock/summary", response_model=StockSummaryReportOut)
def get_stock_summary_report(
    preset: str = Query(default="last_30_days"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    month: str | None = Query(default=None),
    financial_year: str | None = Query(default=None),
    category: StockItemType | None = Query(default=None),
    as_of_date: date | None = Query(default=None),
    _: User = Depends(require_permissions(Permission.REPORTS_VIEW)),
    db: Session = Depends(get_db),
) -> StockSummaryReportOut:
    dr = resolve_date_range(
        preset=preset, date_from=date_from, date_to=date_to, month=month, financial_year=financial_year
    )
    return report_stock_summary(db, dr=dr, category=category, as_of_date=as_of_date)


@router.get("/stock/ledger", response_model=StockLedgerReportOut)
def get_stock_ledger_report(
    preset: str = Query(default="last_30_days"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    month: str | None = Query(default=None),
    financial_year: str | None = Query(default=None),
    stock_item_id: str | None = Query(default=None),
    category: StockItemType | None = Query(default=None),
    movement_type: MovementType | None = Query(default=None),
    reference_doc_type: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    _: User = Depends(require_permissions(Permission.REPORTS_VIEW)),
    db: Session = Depends(get_db),
) -> StockLedgerReportOut:
    dr = resolve_date_range(
        preset=preset, date_from=date_from, date_to=date_to, month=month, financial_year=financial_year
    )
    return report_stock_ledger(
        db,
        dr=dr,
        stock_item_id=stock_item_id,
        category=category,
        movement_type=movement_type,
        reference_doc_type=reference_doc_type,
        page=page,
        page_size=page_size,
    )


@router.get("/production", response_model=ProductionRegisterReportOut)
def get_production_register_report(
    preset: str = Query(default="last_30_days"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    month: str | None = Query(default=None),
    financial_year: str | None = Query(default=None),
    product_id: str | None = Query(default=None),
    _: User = Depends(require_permissions(Permission.REPORTS_VIEW)),
    db: Session = Depends(get_db),
) -> ProductionRegisterReportOut:
    dr = resolve_date_range(
        preset=preset, date_from=date_from, date_to=date_to, month=month, financial_year=financial_year
    )
    return report_production_register(db, dr=dr, product_id=product_id)


@router.get("/production/variance", response_model=ProductionVarianceReportOut)
def get_production_variance_report(
    preset: str = Query(default="last_30_days"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    month: str | None = Query(default=None),
    financial_year: str | None = Query(default=None),
    product_id: str | None = Query(default=None),
    _: User = Depends(require_permissions(Permission.REPORTS_VIEW)),
    db: Session = Depends(get_db),
) -> ProductionVarianceReportOut:
    dr = resolve_date_range(
        preset=preset, date_from=date_from, date_to=date_to, month=month, financial_year=financial_year
    )
    return report_production_variance(db, dr=dr, product_id=product_id)


@router.get("/production/costing", response_model=ProductionCostReportOut)
def get_production_costing_report(
    preset: str = Query(default="last_30_days"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    month: str | None = Query(default=None),
    financial_year: str | None = Query(default=None),
    product_id: str | None = Query(default=None),
    _: User = Depends(require_permissions(Permission.REPORTS_VIEW)),
    db: Session = Depends(get_db),
) -> ProductionCostReportOut:
    dr = resolve_date_range(
        preset=preset, date_from=date_from, date_to=date_to, month=month, financial_year=financial_year
    )
    return report_production_costing(db, dr=dr, product_id=product_id)


@router.get("/payments", response_model=PaymentRegisterReportOut)
def get_payment_register_report(
    preset: str = Query(default="last_30_days"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    month: str | None = Query(default=None),
    financial_year: str | None = Query(default=None),
    customer_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    _: User = Depends(require_permissions(Permission.REPORTS_VIEW)),
    db: Session = Depends(get_db),
) -> PaymentRegisterReportOut:
    dr = resolve_date_range(
        preset=preset, date_from=date_from, date_to=date_to, month=month, financial_year=financial_year
    )
    return report_payments_register(
        db, dr=dr, customer_id=customer_id, page=page, page_size=page_size
    )


@router.get("/receivables", response_model=ReceivablesReportSummaryOut)
def get_receivables_report_audit(
    customer_id: str | None = Query(default=None),
    as_of_date: date | None = Query(default=None),
    _: User = Depends(require_permissions(Permission.REPORTS_VIEW)),
    db: Session = Depends(get_db),
) -> ReceivablesReportSummaryOut:
    return report_receivables_audit(db, customer_id=customer_id, as_of_date=as_of_date)


@router.get("/receivables/ageing", response_model=ReceivablesAgeingAuditOut)
def get_receivables_ageing_report_audit(
    customer_id: str | None = Query(default=None),
    as_of_date: date | None = Query(default=None),
    _: User = Depends(require_permissions(Permission.REPORTS_VIEW)),
    db: Session = Depends(get_db),
) -> ReceivablesAgeingAuditOut:
    return report_receivables_ageing_audit(db, customer_id=customer_id, as_of_date=as_of_date)


@router.get("/export/excel")
def export_report_as_excel(
    report_type: str = Query(...),
    preset: str = Query(default="last_30_days"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    month: str | None = Query(default=None),
    financial_year: str | None = Query(default=None),
    customer_id: str | None = Query(default=None),
    product_id: str | None = Query(default=None),
    supplier_id: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    category: StockItemType | None = Query(default=None),
    movement_type: MovementType | None = Query(default=None),
    stock_item_id: str | None = Query(default=None),
    as_of_date: date | None = Query(default=None),
    _: User = Depends(require_permissions(Permission.REPORTS_EXPORT)),
    db: Session = Depends(get_db),
) -> Response:
    dr = resolve_date_range(
        preset=preset, date_from=date_from, date_to=date_to, month=month, financial_year=financial_year
    )
    title, headers, rows, totals = collect_report_table(
        db,
        report_type=report_type,
        dr=dr,
        customer_id=customer_id,
        product_id=product_id,
        supplier_id=supplier_id,
        status_filter=status_filter,
        category=category,
        movement_type=movement_type,
        stock_item_id=stock_item_id,
        as_of_date=as_of_date,
    )
    return Response(
        content=export_report_xlsx(title, dr, headers, rows, totals),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{report_type}-report.xlsx"'},
    )


@router.get("/export/csv")
def export_report_as_csv(
    report_type: str = Query(...),
    preset: str = Query(default="last_30_days"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    month: str | None = Query(default=None),
    financial_year: str | None = Query(default=None),
    customer_id: str | None = Query(default=None),
    product_id: str | None = Query(default=None),
    supplier_id: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    category: StockItemType | None = Query(default=None),
    movement_type: MovementType | None = Query(default=None),
    stock_item_id: str | None = Query(default=None),
    as_of_date: date | None = Query(default=None),
    _: User = Depends(require_permissions(Permission.REPORTS_EXPORT)),
    db: Session = Depends(get_db),
) -> Response:
    dr = resolve_date_range(
        preset=preset, date_from=date_from, date_to=date_to, month=month, financial_year=financial_year
    )
    title, headers, rows, totals = collect_report_table(
        db,
        report_type=report_type,
        dr=dr,
        customer_id=customer_id,
        product_id=product_id,
        supplier_id=supplier_id,
        status_filter=status_filter,
        category=category,
        movement_type=movement_type,
        stock_item_id=stock_item_id,
        as_of_date=as_of_date,
    )
    return Response(
        content=export_report_csv(title, dr, headers, rows, totals),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{report_type}-report.csv"'},
    )


@router.get("/export/pdf")
def export_report_as_pdf(
    report_type: str = Query(...),
    preset: str = Query(default="last_30_days"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    month: str | None = Query(default=None),
    financial_year: str | None = Query(default=None),
    customer_id: str | None = Query(default=None),
    product_id: str | None = Query(default=None),
    supplier_id: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    category: StockItemType | None = Query(default=None),
    movement_type: MovementType | None = Query(default=None),
    stock_item_id: str | None = Query(default=None),
    as_of_date: date | None = Query(default=None),
    _: User = Depends(require_permissions(Permission.REPORTS_EXPORT)),
    db: Session = Depends(get_db),
) -> Response:
    dr = resolve_date_range(
        preset=preset, date_from=date_from, date_to=date_to, month=month, financial_year=financial_year
    )
    title, headers, rows, totals = collect_report_table(
        db,
        report_type=report_type,
        dr=dr,
        customer_id=customer_id,
        product_id=product_id,
        supplier_id=supplier_id,
        status_filter=status_filter,
        category=category,
        movement_type=movement_type,
        stock_item_id=stock_item_id,
        as_of_date=as_of_date,
    )
    return Response(
        content=export_report_pdf(title, dr, headers, rows, totals),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{report_type}-report.pdf"'},
    )
