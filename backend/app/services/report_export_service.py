import csv
from datetime import date, datetime, timezone
from decimal import Decimal
import io
from typing import Any, List, Tuple
from xml.sax.saxutils import escape as xml_escape
import zipfile

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.inventory import MovementType
from app.models.purchase import PurchaseStatus
from app.models.stock_item import StockItemType
from app.schemas.reports import DateRangeMeta
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


def _fmt_num(val: Any) -> str:
    if isinstance(val, Decimal):
        return f"{val:.2f}" if val.as_tuple().exponent >= -2 else f"{val:.6f}".rstrip("0").rstrip(".") or "0"
    return str(val)


def collect_report_table(
    db: Session,
    *,
    report_type: str,
    dr: DateRangeMeta,
    customer_id: str | None = None,
    product_id: str | None = None,
    supplier_id: str | None = None,
    status_filter: str | None = None,
    category: StockItemType | None = None,
    movement_type: MovementType | None = None,
    stock_item_id: str | None = None,
    as_of_date: date | None = None,
) -> Tuple[str, List[str], List[List[Any]], List[Any]]:
    """Build normalized (title, headers, rows, totals_row) matching frontend API tables."""
    rt = report_type.strip().lower()

    if rt == "sales":
        rep = report_sales_register(
            db, dr=dr, customer_id=customer_id, product_id=product_id, page=1, page_size=5000
        )
        headers = [
            "Invoice No", "Invoice Date", "Customer", "Customer GSTIN", "State",
            "Product", "HSN", "Qty", "Taxable", "CGST", "SGST", "IGST", "Total", "Payment Status",
        ]
        rows = [
            [
                r.invoice_number, r.invoice_date.isoformat(), r.customer_name, r.customer_gstin, r.state,
                r.product_name, r.hsn_code, r.quantity, r.taxable_value, r.cgst, r.sgst, r.igst, r.invoice_total, r.payment_status,
            ]
            for r in rep.rows
        ]
        totals = [
            "TOTAL", "", "", "", "", "", "", "",
            rep.total_taxable, rep.total_cgst, rep.total_sgst, rep.total_igst, rep.total_invoice_value, "",
        ]
        return "Sales Register", headers, rows, totals

    if rt == "sales_customers":
        rep = report_sales_by_customer(db, dr=dr, customer_id=customer_id)
        headers = ["Customer", "GSTIN", "State", "Orders", "Invoices", "Taxable", "GST", "Invoice Value", "Collected", "Outstanding"]
        rows = [
            [r.customer_name, r.customer_gstin, r.state, r.total_orders, r.total_invoices, r.total_taxable_sales, r.total_gst, r.total_invoice_value, r.amount_collected, r.outstanding_amount]
            for r in rep.rows
        ]
        totals = ["TOTAL", "", "", "", "", "", "", rep.total_invoice_value, rep.total_collected, rep.total_outstanding]
        return "Customer-wise Sales Report", headers, rows, totals

    if rt == "sales_products":
        rep = report_sales_by_product(db, dr=dr, product_id=product_id)
        headers = ["Product", "SKU", "Packets Sold", "Taxable Sales", "Avg Price", "Tax", "Contribution %"]
        rows = [
            [r.product_name, r.sku, r.total_packets_sold, r.sales_value, r.average_selling_price, r.tax_amount, r.revenue_contribution_pct]
            for r in rep.rows
        ]
        totals = ["TOTAL", "", "", rep.total_taxable_sales, "", rep.total_tax, Decimal("100.00")]
        return "Product-wise Sales Report", headers, rows, totals

    if rt == "sales_salesmen":
        rep = report_sales_by_salesman(db, dr=dr)
        headers = ["Salesman", "Email", "Orders", "Approved", "Dispatched", "Sales Value"]
        rows = [[r.salesman_name, r.salesman_email, r.orders_count, r.approved_orders, r.dispatched_orders, r.sales_value] for r in rep.rows]
        totals = ["TOTAL", "", "", "", "", rep.total_sales_value]
        return "Salesman Performance Report", headers, rows, totals

    if rt == "gst_outward":
        rep = report_gst_outward_supplies(db, dr=dr)
        headers = ["GST Rate %", "Taxable Value", "CGST", "SGST", "IGST", "Total Tax"]
        rows = [[r.gst_rate, r.taxable_value, r.cgst_amount, r.sgst_amount, r.igst_amount, r.total_tax] for r in rep.by_rate]
        totals = ["TOTAL", rep.total_taxable_outward, rep.total_cgst, rep.total_sgst, rep.total_igst, (rep.total_cgst + rep.total_sgst + rep.total_igst)]
        return "GST Outward Supplies Summary (Indicative)", headers, rows, totals

    if rt == "gst_hsn":
        rep = report_gst_hsn_summary(db, dr=dr)
        headers = ["HSN Code", "Description", "UQC", "Quantity", "Taxable Value", "CGST", "SGST", "IGST", "Total Value"]
        rows = [[r.hsn_code, r.description, r.uqc, r.total_quantity, r.taxable_value, r.cgst_amount, r.sgst_amount, r.igst_amount, r.total_value] for r in rep.rows]
        totals = ["TOTAL", "", "", "", rep.total_taxable_value, "", "", "", rep.total_taxable_value + rep.total_tax]
        return "GST HSN Summary Report (Indicative)", headers, rows, totals

    if rt == "purchases":
        st_enum = PurchaseStatus(status_filter) if status_filter else None
        rep = report_purchase_register(
            db, dr=dr, supplier_id=supplier_id, stock_item_id=stock_item_id, status_filter=st_enum, page=1, page_size=5000
        )
        headers = ["Reference", "Date", "Supplier", "GSTIN", "Item", "Qty", "Unit", "Rate", "Taxable", "GST", "Total", "Status"]
        rows = [
            [r.reference_number, r.purchase_date.isoformat(), r.supplier_name, r.supplier_gstin, r.item_name, r.quantity, r.unit_symbol, r.purchase_rate, r.taxable_amount, r.gst_amount, r.total_purchase_amount, r.status]
            for r in rep.rows
        ]
        totals = ["POSTED TOTAL", "", "", "", "", "", "", "", "", "", rep.posted_total, ""]
        return "Purchase Register", headers, rows, totals

    if rt == "stock_summary":
        rep = report_stock_summary(db, dr=dr, category=category, as_of_date=as_of_date)
        headers = ["Item", "SKU", "Category", "Opening", "Receipts", "Issues", "Adjustments", "Closing", "Unit", "Avg Rate", "Valuation", "Reorder", "Status"]
        rows = [
            [r.item_name, r.sku, r.category, r.opening_stock, r.total_receipts, r.total_issues, r.adjustments, r.closing_stock, r.base_unit, r.weighted_average_rate, r.stock_valuation, r.reorder_level, r.stock_status]
            for r in rep.rows
        ]
        totals = ["TOTAL", "", "", "", "", "", "", "", "", "", rep.total_valuation, "", ""]
        return f"Stock Summary ({rep.category_filter}) as of {rep.as_of_date.isoformat()}", headers, rows, totals

    if rt == "stock_ledger":
        rep = report_stock_ledger(
            db, dr=dr, stock_item_id=stock_item_id, category=category, movement_type=movement_type, page=1, page_size=5000
        )
        headers = ["Tx Date", "Item", "SKU", "Type", "Source Doc", "Doc ID", "Qty In", "Qty Out", "Balance", "Unit Cost", "Value", "Created By"]
        rows = [
            [r.transaction_date.strftime("%Y-%m-%d %H:%M"), r.item_name, r.sku, r.movement_type, r.source_document, r.source_document_id, r.quantity_in, r.quantity_out, r.running_balance, r.unit_valuation, r.movement_value, r.created_by_email]
            for r in rep.rows
        ]
        totals = ["TOTAL", "", "", "", "", "", rep.total_quantity_in, rep.total_quantity_out, "", "", "", ""]
        return "Stock Ledger Report", headers, rows, totals

    if rt == "production":
        rep = report_production_register(db, dr=dr, product_id=product_id)
        headers = ["Run ID", "Product", "Batch", "Date", "BOM v", "Planned", "Good Output", "Wastage", "Supervisor", "Total Cost", "Cost/Pkt", "Status"]
        rows = [
            [r.order_number, r.product_name, r.batch_number, r.production_date.isoformat(), r.bom_version, r.planned_output, r.actual_good_output, r.wastage, r.supervisor_email, r.total_production_cost, r.cost_per_packet, r.status]
            for r in rep.rows
        ]
        totals = ["TOTAL", "", "", "", "", "", rep.total_good_output, "", "", rep.total_production_cost, "", ""]
        return "Production Register", headers, rows, totals

    if rt == "production_variance":
        rep = report_production_variance(db, dr=dr, product_id=product_id)
        headers = ["Run", "Product", "Material", "Planned", "Actual", "Diff", "Variance %", "Status", "Flagged"]
        rows = [
            [m.order_number, m.product_name, m.material_name, m.planned_quantity, m.actual_quantity, m.difference, m.variance_pct, m.status, "YES" if m.exceeds_tolerance else "NO"]
            for m in rep.material_rows
        ]
        totals = ["FLAGGED VARIANCES", "", "", "", "", "", "", "", rep.flagged_count]
        return "Production Variance Report", headers, rows, totals

    if rt == "production_costing":
        rep = report_production_costing(db, dr=dr, product_id=product_id)
        headers = ["Run", "Product", "Good Out", "Raw Mat", "Packaging", "Overhead", "Total Cost", "Cost/Pkt", "Margin %"]
        rows = [
            [r["order_number"], r["product_name"], r["actual_good_output"], r["raw_material_cost"], r["packaging_cost"], r["total_overhead_cost"], r["total_production_cost"], r["cost_per_packet_display"], r["gross_margin_pct"]]
            for r in rep.rows
        ]
        totals = ["TOTAL", "", "", rep.total_material_cost, rep.total_packaging_cost, rep.total_expense_cost, rep.total_production_cost, "", ""]
        return "Production Cost Report", headers, rows, totals

    if rt == "payments":
        rep = report_payments_register(db, dr=dr, customer_id=customer_id, page=1, page_size=5000)
        headers = ["Payment Ref", "Customer", "Date", "Method", "Received", "Allocated", "Unallocated", "Status"]
        rows = [
            [r.payment_reference, r.customer_name, r.payment_date.isoformat(), r.payment_method, r.payment_amount, r.allocated_amount, r.unallocated_amount, r.status]
            for r in rep.rows
        ]
        totals = ["TOTAL", "", "", "", rep.total_received, rep.total_allocated, rep.total_unallocated, ""]
        return "Customer Payment Register", headers, rows, totals

    if rt == "receivables":
        rep = report_receivables_audit(db, customer_id=customer_id, as_of_date=as_of_date or dr.date_to)
        headers = ["Customer", "Invoice #", "Invoice Date", "Due Date", "Total", "Paid", "Outstanding", "Status", "Ageing"]
        rows = [
            [r.customer_name, r.invoice_number, r.invoice_date.isoformat(), r.due_date.isoformat(), r.invoice_amount, r.paid_amount, r.outstanding_amount, r.payment_status, r.ageing_category]
            for r in rep.rows
        ]
        totals = ["TOTAL", "", "", "", rep.total_invoiced, rep.total_paid, rep.total_outstanding, "", ""]
        return "Receivables Report", headers, rows, totals

    if rt == "receivables_ageing":
        rep = report_receivables_ageing_audit(db, customer_id=customer_id, as_of_date=as_of_date or dr.date_to)
        headers = ["Customer", "Invoice #", "Invoice Date", "Due Date", "Amount", "Paid", "Outstanding", "Days Overdue", "Ageing Category"]
        rows = [
            [r.customer_name, r.invoice_number, r.invoice_date.isoformat(), r.due_date.isoformat(), r.invoice_amount, r.paid_amount, r.outstanding_amount, r.days_overdue, r.ageing_category]
            for r in rep.rows
        ]
        totals = ["TOTAL", "", "", "", "", "", rep.total_outstanding, "", ""]
        return f"Receivables Ageing Report (As of {rep.as_of_date.isoformat()})", headers, rows, totals

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"Unknown report_type '{report_type}'.",
    )


def export_report_csv(
    title: str, dr: DateRangeMeta, headers: List[str], rows: List[List[Any]], totals: List[Any]
) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([f"FactoryFlow ERP - {title}"])
    writer.writerow([f"Reporting Period: {dr.date_from.isoformat()} to {dr.date_to.isoformat()}"])
    writer.writerow(headers)
    for row in rows:
        writer.writerow([_fmt_num(c) for c in row])
    if totals:
        writer.writerow([_fmt_num(c) for c in totals])
    return buf.getvalue().encode("utf-8")


def _col_letter(idx: int) -> str:
    res = ""
    while idx > 0:
        idx, rem = divmod(idx - 1, 26)
        res = chr(65 + rem) + res
    return res


def export_report_xlsx(
    title: str, dr: DateRangeMeta, headers: List[str], rows: List[List[Any]], totals: List[Any]
) -> bytes:
    """Generate a genuine standards-compliant OOXML .xlsx workbook using Python stdlib zipfile."""
    sheet_rows: List[List[Any]] = [
        [f"FactoryFlow ERP - {title}"],
        [f"Period: {dr.date_from.isoformat()} to {dr.date_to.isoformat()}"],
        headers,
        *rows,
    ]
    if totals:
        sheet_rows.append(totals)

    xml_rows = []
    for r_idx, row in enumerate(sheet_rows, start=1):
        cells = []
        for c_idx, val in enumerate(row, start=1):
            ref = f"{_col_letter(c_idx)}{r_idx}"
            if isinstance(val, (int, float, Decimal)) and not isinstance(val, bool):
                cells.append(f'<c r="{ref}" t="n"><v>{val}</v></c>')
            else:
                text = xml_escape(str(val) if val is not None else "")
                cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>')
        xml_rows.append(f'<row r="{r_idx}">{"".join(cells)}</row>')

    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(xml_rows)}</sheetData>'
        "</worksheet>"
    )

    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Report" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    wb_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        "</Relationships>"
    )
    styles = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
        '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
        '<borders count="1"><border/></borders>'
        '<cellStyleXfs count="1"><xf/></cellStyleXfs>'
        '<cellXfs count="1"><xf xfId="0"/></cellXfs>'
        "</styleSheet>"
    )

    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("xl/workbook.xml", workbook)
        zf.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        zf.writestr("xl/styles.xml", styles)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return out.getvalue()


def export_report_pdf(
    title: str, dr: DateRangeMeta, headers: List[str], rows: List[List[Any]], totals: List[Any]
) -> bytes:
    """Render a multi-page PDF 1.4 report with factory header, filters, totals, and page numbers."""
    settings = get_settings()
    gen_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    header_line = " | ".join(h[:12] for h in headers)
    table_lines = [
        " | ".join(_fmt_num(c)[:12] for c in row) for row in rows
    ]
    if totals:
        table_lines.append("-" * 86)
        table_lines.append(" | ".join(_fmt_num(c)[:12] for c in totals))
    if not rows:
        table_lines.append("No records match the selected reporting filters.")

    rows_per_page = 36
    chunks = [
        table_lines[i : i + rows_per_page]
        for i in range(0, max(1, len(table_lines)), rows_per_page)
    ]
    total_pages = len(chunks)

    def _esc(text: str) -> str:
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    # Build PDF object stream dynamically: 1=Catalog, 2=Pages, 3=Font, then pairs of (Page, Content)
    page_ids = [4 + idx * 2 for idx in range(total_pages)]
    objects: List[bytes] = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        f"2 0 obj << /Type /Pages /Kids [{' '.join(f'{pid} 0 R' for pid in page_ids)}] /Count {total_pages} >> endobj\n".encode("ascii"),
        b"3 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Courier >> endobj\n",
    ]

    for idx, chunk in enumerate(chunks):
        page_obj_id = 4 + idx * 2
        content_obj_id = page_obj_id + 1
        lines = [
            f"{settings.factory_name} | GSTIN: {settings.factory_gstin}",
            f"Report: {title}",
            f"Filters: {dr.date_from.isoformat()} to {dr.date_to.isoformat()} ({dr.preset}) | Generated: {gen_at}",
            "=" * 86,
            header_line,
            "-" * 86,
            *chunk,
            "=" * 86,
            f"Page {idx + 1} of {total_pages}",
        ]
        cmds = ["BT", "/F1 8 Tf", "28 765 Td", "12 TL"]
        for li, line in enumerate(lines):
            cmds.append(f"({_esc(line)}) Tj" if li == 0 else f"T* ({_esc(line)}) Tj")
        cmds.append("ET")
        stream = "\n".join(cmds).encode("latin-1", errors="replace")

        objects.append(
            (
                f"{page_obj_id} 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_obj_id} 0 R >> endobj\n"
            ).encode("ascii")
        )
        objects.append(
            f"{content_obj_id} 0 obj << /Length {len(stream)} >>\nstream\n".encode("ascii")
            + stream
            + b"\nendstream\nendobj\n"
        )

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj)
    xref_pos = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii"))
    for off in offsets[1:]:
        pdf.extend(f"{off:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        (
            f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_pos}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(pdf)
