# FactoryFlow – Phase 7: Owner Dashboard & Audit Reports Reference

## 1. Report Sources & Reconciliation Rules
Every Phase 7 report queries live SQLAlchemy/PostgreSQL models directly and sets reconciliation flags comparing report sums to source tables:
- **Sales Register & Product/Customer/Salesman Sales**: Derived from `invoices` + `invoice_items` + `sales_orders` + `payment_allocations`. Draft/submitted/rejected/cancelled orders are tracked separately and excluded from invoiced revenue totals.
- **GST Outward Supply & HSN Summary**: Indicative mapping to `GSTR-1` / `GSTR-3B` outward tax liability buckets (`CGST`, `SGST`, `IGST`, `B2B` vs `B2C`, HSN totals, and `CreditNote` adjustments). **Note:** Indicative internal reporting only — not an official GST portal filing; validate with a qualified tax professional before real filing.
- **Purchase Register**: Derived from `purchases` + `purchase_items`, distinguishing `POSTED`, `DRAFT`/`REVIEWED`, and `CANCELLED` without fabricating missing GST values.
- **Historical Stock Summary & Stock Ledger**: Reconstructs `opening_stock`, `receipts`, `issues`, `adjustments`, `closing_stock`, and `stock_valuation` directly from `stock_ledger` entries up to the selected `as_of_date` cut-off — never returning current projections for past dates.
- **Production Register, Variance & Costing**: Derived from `production_runs`, `production_materials`, `production_wastage`, `stock_ledger` (`PRODUCTION_ISSUE`), and posted `production_expenses`.
- **Payments, Receivables & Ageing**: Derived from posted `payments`, `payment_allocations`, `invoices`, and `credit_notes` using configurable `default_payment_term_days = 30`.

## 2. Export Formats (`/api/v1/reports/export/*`)
- **Excel (`.xlsx`)**: OOXML workbook with report title, date range, column headers, numeric cells, and summary totals.
- **CSV (`.csv`)**: UTF-8 tabular export matching active frontend filters.
- **PDF (`.pdf`)**: Paginated PDF 1.4 report with factory header/GSTIN, title, active filters, generated UTC timestamp, table rows, summary totals, and `Page X of Y` footers.
