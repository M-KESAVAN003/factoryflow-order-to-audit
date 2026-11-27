# FactoryFlow – Phase 6: Production Costing & Payment Management

## 1. Production Costing Methodology (`Decimal` Precision)

- **Actual Consumption Valuation**: Uses actual issued quantities (`total_consumed_base_qty`) valued from `StockLedger` (`PRODUCTION_ISSUE`) / weighted-average `StockBalance`, never planned BOM quantities.
- **Damaged Packaging Inclusion**: `6` damaged pouches consumed alongside `188` good pouches = `194` pouches (`₹485.00`), fully included in run cost.
- **Overhead Allocation**: Tracks `LABOUR`, `GAS`, `ELECTRICITY`, `POWER`, `MAINTENANCE`, and `OTHER_OVERHEAD` expenses (`DRAFT -> POSTED -> REVERSED`).
- **Pre-GST Gross Margin**: Uses selling price before GST (`₹50.00`), keeping GST collected strictly separate from revenue.

### Benchmark Run Cost Sheet (`Murukku 200 g`, 188 good packets)
- **Raw Materials (`₹3,435.00`)**: Flour `40 × ₹43.125 = ₹1,725.00`, Oil `10.5 × ₹140 = ₹1,470.00`, Spice `1.2 × ₹200 = ₹240.00`
- **Packaging (`₹620.00`)**: Pouches `194 × ₹2.50 = ₹485.00`, Cartons `9 × ₹15 = ₹135.00`
- **Material & Packaging Subtotal**: `₹4,055.00`
- **Additional Expenses**: Labour `₹1,200.00`, Gas & Power `₹600.00` (`₹1,800.00` overhead)
- **Total Production Cost**: **`₹5,855.00`**
- **Cost / Good Packet**: `5855 / 188 = ₹31.143617` exact (**`₹31.14`** display)
- **Gross Profit / Packet**: `₹50.00 - ₹31.143617 =` **`₹18.86`** (`37.71%` margin)

---

## 2. Customer Payments, Receivables & Ageing

- **Retailer A Payment Benchmark**:
  - Invoice `INV/2026-27/0001`: `₹7,875.00`
  - Partial Payment `PAY-BENCH-001` (`UPI`): `₹4,000.00`
  - Derived Outstanding (`7875 - 4000`): **`₹3,875.00`** (`PARTIAL`)
- **Multi-invoice Allocation & Advances**: Unallocated payments are tracked as `unallocated_advance` and can be split across multiple invoices later; allocations cannot exceed remaining advance or invoice outstanding (`422`).
- **Receivables Ageing**: Uses configurable `default_payment_term_days = 30` (`due_date = invoice_date + 30 days`) across 5 buckets: `Current / Not Due`, `1-30 days overdue`, `31-60 days overdue`, `61-90 days overdue`, `More than 90 days overdue`.
