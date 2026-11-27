# FactoryFlow – Accountant & Auditor Read-Only Guide

## 1. Auditor Permissions (`auditor` Role)
- **Granted (`200 OK`)**: `audit:read`, `bom:read`, `production_runs:read`, `inventory:read`, `purchases:read`, `sales_orders:read`, `invoices:read`, `dispatches:read`, `costing:read`, `payments:read`, `receivables:read`, `reports:view`, `reports:export`, `/api/v1/dashboard/finance`.
- **Blocked (`403 Forbidden`)**: Creating/editing/approving orders, posting purchases or stock adjustments, posting/cancelling production runs, modifying invoices, recording payments, mutating audit logs, and `/api/v1/dashboard/owner` (reserved for `admin`).

## 2. End-to-End Reconciliation Checklist
1. Compare **Sales Register** (`total_invoice_value`) against **GST Summary** (`total_taxable_outward + CGST + SGST + IGST`) — both match `₹7,875.00` (`₹7,500.00 + ₹187.50 + ₹187.50`).
2. Compare **Stock Summary** closing quantity for `Murukku 200 g` on `2026-11-20` (`238`) vs `2026-11-26` (`88`) with **Stock Ledger** (`PRODUCTION_OUTPUT +188` and `SALES_DISPATCH -150`).
3. Verify **Production Cost Report** (`₹5,855.00`) equals `Material+Packaging (₹4,055.00) + Labour (₹1,200.00) + Gas/Power (₹600.00)`, yielding `₹31.14/pkt` and `37.71%` gross margin.
4. Confirm **Receivables Report** (`₹3,875.00`) reconciles `Retailer A Invoice (₹7,875.00) - Payment PAY-2026-0001 (₹4,000.00)`.
