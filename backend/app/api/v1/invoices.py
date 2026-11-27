from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip, require_permissions
from app.core.database import get_db
from app.core.permissions import Permission
from app.models.user import User
from app.schemas.costing_payment import InvoicePaymentsDetailOut
from app.schemas.master_data import PaginatedResponse
from app.schemas.sales import CreditNoteCreate, CreditNoteOut, InvoiceCreate, InvoiceOut
from app.services.gst_service import build_gst_invoice_pdf
from app.services.payment_service import get_invoice_payments_detail
from app.services.sales_service import (
    create_credit_note,
    create_invoice,
    get_invoice_or_404,
    list_invoices,
    to_invoice_out,
)

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.get("", response_model=PaginatedResponse[InvoiceOut])
def get_invoices(
    search: str | None = Query(default=None),
    customer_id: str | None = Query(default=None),
    financial_year: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_permissions(Permission.INVOICES_READ)),
    db: Session = Depends(get_db),
) -> PaginatedResponse[InvoiceOut]:
    items, total = list_invoices(
        db,
        search=search,
        customer_id=customer_id,
        financial_year=financial_year,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[to_invoice_out(inv) for inv in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
def post_create_invoice(
    payload: InvoiceCreate,
    request: Request,
    actor: User = Depends(require_permissions(Permission.INVOICES_MANAGE)),
    db: Session = Depends(get_db),
) -> InvoiceOut:
    invoice = create_invoice(db, payload, actor=actor, ip_address=get_client_ip(request))
    return to_invoice_out(invoice)


@router.get("/{invoice_id}", response_model=InvoiceOut)
def get_invoice_detail(
    invoice_id: str,
    _: User = Depends(require_permissions(Permission.INVOICES_READ)),
    db: Session = Depends(get_db),
) -> InvoiceOut:
    return to_invoice_out(get_invoice_or_404(db, invoice_id))


@router.get("/{invoice_id}/pdf")
def get_invoice_pdf(
    invoice_id: str,
    _: User = Depends(require_permissions(Permission.INVOICES_READ)),
    db: Session = Depends(get_db),
) -> Response:
    invoice = get_invoice_or_404(db, invoice_id)
    pdf_bytes = build_gst_invoice_pdf(invoice)
    safe_name = invoice.invoice_number.replace("/", "-")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.pdf"'},
    )


@router.post("/{invoice_id}/credit-notes", response_model=CreditNoteOut, status_code=status.HTTP_201_CREATED)
def post_create_credit_note(
    invoice_id: str,
    payload: CreditNoteCreate,
    request: Request,
    actor: User = Depends(require_permissions(Permission.INVOICES_MANAGE)),
    db: Session = Depends(get_db),
) -> CreditNoteOut:
    cn = create_credit_note(
        db, invoice_id, payload, actor=actor, ip_address=get_client_ip(request)
    )
    return CreditNoteOut(
        id=cn.id,
        credit_note_number=cn.credit_note_number,
        invoice_id=cn.invoice_id,
        financial_year=cn.financial_year,
        credit_date=cn.credit_date,
        reason=cn.reason,
        amount=cn.amount,
        created_by_email=cn.creator.email,
        created_at=cn.created_at,
    )


@router.get("/{invoice_id}/payments", response_model=InvoicePaymentsDetailOut)
def get_invoice_payments(
    invoice_id: str,
    _: User = Depends(require_permissions(Permission.INVOICES_READ)),
    db: Session = Depends(get_db),
) -> InvoicePaymentsDetailOut:
    return get_invoice_payments_detail(db, invoice_id)
