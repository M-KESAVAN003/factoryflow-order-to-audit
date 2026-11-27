# FactoryFlow – Phase 5: Sales Order Management & GST Billing

## 1. End-to-End Sales Workflow

```
Salesman (Mobile Order Entry)
  → SUBMITTED (Assigned Customers, auto-fetched Selling Price + GST Preview)
  → Admin Stock Check & Review (UNDER_REVIEW / edit pending qty or price)
  → Stock Available?
       ├── YES → APPROVED (with StockBalance row locks preventing overselling)
       │         → POST /api/v1/invoices → INVOICED (immutable Tax Invoice PDF, stock untouched)
       │         → POST /api/v1/dispatches → DISPATCHED (atomic StockLedger SALES_DISPATCH OUT)
       └── NO  → AWAITING_STOCK (or PARTIALLY_FULFILLED) — overselling & premature invoicing blocked
```

## 2. GST Supply & Calculation Rules (`Decimal` NUMERIC Arithmetic)
- **Factory Origin**: Tamil Nadu (`33`), GSTIN `33AAACF1234F1Z5`
- **Intra-State (e.g. Retailer A – Tamil Nadu)**: `CGST 2.5% + SGST 2.5%`
- **Inter-State (e.g. Distributor B – Karnataka)**: `IGST 5%`
- **Sequential Numbering**: `INV/{FY}/{seq:04d}` protected by database uniqueness `(financial_year, sequence_number)` and `sales_order_id`. Posted invoices are immutable; corrections issue traceable `CreditNote` records (`CN/{FY}/{seq:04d}`).

## 3. Benchmark Results

### Retailer A (Tamil Nadu)
- Finished stock before dispatch: **238 packets**
- Quantity: **150 packets** × `₹50.00` = **₹7,500.00** taxable value
- **CGST (2.5%)**: `₹187.50` | **SGST (2.5%)**: `₹187.50` | **Grand Total**: `₹7,875.00`
- Closing finished stock after dispatch: **88 packets**

### Distributor B Shortage (Karnataka)
- Requested: **120 packets** | Available: **88 packets** | Shortage: **32 packets**
- Tax Preview (Inter-state `IGST 5%`): Subtotal `₹6,000.00`, IGST `₹300.00`, Total `₹6,300.00`
- Held in `AWAITING_STOCK`; invoicing and dispatch remain blocked (`422`) until stock is replenished.
