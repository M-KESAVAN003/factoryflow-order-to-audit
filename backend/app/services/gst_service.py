from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from app.models.sales import Invoice, TaxType

AMT_PREC = Decimal("0.01")
RATE_PREC = Decimal("0.01")


@dataclass(frozen=True)
class GstComputation:
    tax_type: TaxType
    taxable_value: Decimal
    cgst_rate: Decimal
    sgst_rate: Decimal
    igst_rate: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    total_tax: Decimal
    line_total: Decimal


def get_financial_year(doc_date: date) -> str:
    """Return Indian GST financial year string e.g. '2026-27'."""
    if doc_date.month >= 4:
        return f"{doc_date.year}-{str(doc_date.year + 1)[-2:]}"
    return f"{doc_date.year - 1}-{str(doc_date.year)[-2:]}"


def determine_tax_type(
    factory_state: str,
    customer_state: str,
    factory_state_code: str | None = None,
    customer_state_code: str | None = None,
) -> TaxType:
    """Determine intra-state (CGST+SGST) vs inter-state (IGST) supply."""
    if factory_state_code and customer_state_code:
        if factory_state_code.strip() == customer_state_code.strip():
            return TaxType.INTRA_STATE
        return TaxType.INTER_STATE
    if factory_state.strip().lower() == customer_state.strip().lower():
        return TaxType.INTRA_STATE
    return TaxType.INTER_STATE


def compute_line_gst(
    *,
    quantity: Decimal,
    unit_price: Decimal,
    gst_rate: Decimal,
    tax_type: TaxType,
) -> GstComputation:
    """Compute exact Decimal GST breakdown rounded to 2 decimal places."""
    taxable = (Decimal(quantity) * Decimal(unit_price)).quantize(AMT_PREC, rounding=ROUND_HALF_UP)
    rate = Decimal(gst_rate).quantize(RATE_PREC, rounding=ROUND_HALF_UP)

    if tax_type == TaxType.INTRA_STATE:
        half_rate = (rate / Decimal("2")).quantize(RATE_PREC, rounding=ROUND_HALF_UP)
        cgst = (taxable * half_rate / Decimal("100")).quantize(AMT_PREC, rounding=ROUND_HALF_UP)
        sgst = (taxable * half_rate / Decimal("100")).quantize(AMT_PREC, rounding=ROUND_HALF_UP)
        igst = Decimal("0.00")
        cgst_rate, sgst_rate, igst_rate = half_rate, half_rate, Decimal("0.00")
    else:
        igst = (taxable * rate / Decimal("100")).quantize(AMT_PREC, rounding=ROUND_HALF_UP)
        cgst = Decimal("0.00")
        sgst = Decimal("0.00")
        cgst_rate, sgst_rate, igst_rate = Decimal("0.00"), Decimal("0.00"), rate

    total_tax = (cgst + sgst + igst).quantize(AMT_PREC, rounding=ROUND_HALF_UP)
    line_total = (taxable + total_tax).quantize(AMT_PREC, rounding=ROUND_HALF_UP)
    return GstComputation(
        tax_type=tax_type,
        taxable_value=taxable,
        cgst_rate=cgst_rate,
        sgst_rate=sgst_rate,
        igst_rate=igst_rate,
        cgst_amount=cgst,
        sgst_amount=sgst,
        igst_amount=igst,
        total_tax=total_tax,
        line_total=line_total,
    )


_ONES = [
    "",
    "One",
    "Two",
    "Three",
    "Four",
    "Five",
    "Six",
    "Seven",
    "Eight",
    "Nine",
    "Ten",
    "Eleven",
    "Twelve",
    "Thirteen",
    "Fourteen",
    "Fifteen",
    "Sixteen",
    "Seventeen",
    "Eighteen",
    "Nineteen",
]
_TENS = [
    "",
    "",
    "Twenty",
    "Thirty",
    "Forty",
    "Fifty",
    "Sixty",
    "Seventy",
    "Eighty",
    "Ninety",
]


def _two_digits(n: int) -> str:
    if n == 0:
        return ""
    if n < 20:
        return _ONES[n]
    return f"{_TENS[n // 10]} {_ONES[n % 10]}".strip()


def _three_digits(n: int) -> str:
    if n == 0:
        return ""
    if n < 100:
        return _two_digits(n)
    rem = n % 100
    head = f"{_ONES[n // 100]} Hundred"
    return f"{head} {_two_digits(rem)}".strip() if rem else head


def _indian_int_words(n: int) -> str:
    if n == 0:
        return "Zero"
    parts = []
    crore, rem = divmod(n, 10_000_000)
    lakh, rem = divmod(rem, 100_000)
    thousand, rest = divmod(rem, 1_000)
    if crore:
        parts.append(f"{_three_digits(crore)} Crore")
    if lakh:
        parts.append(f"{_two_digits(lakh)} Lakh")
    if thousand:
        parts.append(f"{_two_digits(thousand)} Thousand")
    if rest:
        parts.append(_three_digits(rest))
    return " ".join(parts).strip()


def amount_to_inr_words(amount: Decimal) -> str:
    """Convert an INR Decimal amount to formal Indian GST invoice wording."""
    q = Decimal(amount).quantize(AMT_PREC, rounding=ROUND_HALF_UP)
    rupees = int(q)
    paise = int(((q - Decimal(rupees)) * Decimal("100")).quantize(Decimal("1")))
    if paise > 0:
        return f"Rupees {_indian_int_words(rupees)} and {_two_digits(paise)} Paise Only"
    return f"Rupees {_indian_int_words(rupees)} Only"


def format_place_of_supply(state: str, state_code: str) -> str:
    return f"{state} ({state_code})" if state_code else state


def build_gst_invoice_pdf(invoice: Invoice) -> bytes:
    """Render a valid multi-section PDF 1.4 GST Tax Invoice document."""
    lines = [
        "TAX INVOICE (ORIGINAL FOR RECIPIENT)",
        "=" * 78,
        f"Seller: {invoice.factory_name}",
        f"Address: {invoice.factory_address}",
        f"GSTIN: {invoice.factory_gstin} | State: {invoice.factory_state} ({invoice.factory_state_code})",
        "-" * 78,
        f"Invoice No: {invoice.invoice_number}   | Date: {invoice.invoice_date.isoformat()}",
        f"Financial Year: {invoice.financial_year}       | Supply Type: {invoice.tax_type.value}",
        f"Customer: {invoice.customer_name}",
        f"Customer GSTIN: {invoice.customer_gstin}",
        f"Billing Address: {invoice.billing_address}",
        f"Place of Supply: {invoice.place_of_supply}",
        "-" * 78,
        "Product / Pack           | HSN      | Qty     | Rate    | Taxable",
        "-" * 78,
    ]
    for item in invoice.items:
        qty_disp = f"{Decimal(item.quantity):.2f}"
        lines.append(
            f"{(item.product_name + ' ' + item.pack_size)[:24]:<24} | {item.hsn_code:<8} | "
            f"{qty_disp:<7} | {item.unit_price:<7.2f} | INR {item.taxable_value:.2f}"
        )
    lines.extend(
        [
            "-" * 78,
            f"Taxable Value: INR {invoice.subtotal:.2f}",
            f"CGST:          INR {invoice.cgst_amount:.2f}",
            f"SGST:          INR {invoice.sgst_amount:.2f}",
            f"IGST:          INR {invoice.igst_amount:.2f}",
            f"Total Tax:     INR {invoice.tax_amount:.2f}",
            f"Grand Total:   INR {invoice.grand_total:.2f}",
            "-" * 78,
            f"Amount in Words: {invoice.amount_in_words}",
            "=" * 78,
            "Authorized Signatory - FactoryFlow ERP",
        ]
    )

    def _esc(text: str) -> str:
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    cmds = ["BT", "/F1 9 Tf", "36 760 Td", "13 TL"]
    for idx, line in enumerate(lines):
        cmds.append(f"({_esc(line)}) Tj" if idx == 0 else f"T* ({_esc(line)}) Tj")
    cmds.append("ET")
    stream = "\n".join(cmds).encode("latin-1", errors="replace")

    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        (
            b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n"
        ),
        b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Courier >> endobj\n",
        (
            f"5 0 obj << /Length {len(stream)} >>\nstream\n".encode("ascii")
            + stream
            + b"\nendstream\nendobj\n"
        ),
    ]

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
