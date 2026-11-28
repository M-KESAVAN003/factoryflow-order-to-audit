# FactoryFlow – Phase 9 Final QA & Benchmark Validation Report

## 1. Test Environment & Database Setup
- **Backend Runtime**: Python `3.13.17`, FastAPI `0.115.6`, SQLAlchemy `2.0.36`, Alembic `1.14.0`, Pydantic `2.10.3`.
- **Frontend Runtime**: Node.js `v20.18.0`, React `18.3.1`, TypeScript `5.6.3`, Vite `6.4.6`, Vitest `2.1.9`.
- **Database Isolation**:
  - `backend/scripts/benchmark_reset_seed.py` enforces strict safety guards (`ENVIRONMENT != production`, target URL must differ from `DATABASE_URL` / `settings.database_url`, PostgreSQL DB names must contain `test`, `benchmark`, or `qa`) and verifies idempotent double-seeding across Alembic head `0008_phase10_owner_role` (`6` base role accounts including `owner@factoryflow.io`).
  - Automated backend suites (`pytest`) ran against isolated in-memory / temporary SQLite test databases matching the Alembic schema (`0001_phase1` through `0008_phase10_owner_role`).
  - **Environment Disclosure**: Neither a live Neon PostgreSQL instance (`backend/.env` / `DATABASE_URL`) nor Playwright/Chromium is provisioned in the local environment; live PostgreSQL network execution, Render/Vercel live deployments, and physical Android Chrome offline installation remain unverified outside isolated SQLite / JSDOM runs.

---

## 2. Full 10-Step Internship Benchmark Results
Executed sequentially without duplicate transactions in `backend/tests/test_phase9_full_system_e2e.py::test_complete_10_step_internship_benchmark_reports_exports_and_sync`:

| Step | Scenario Metric | Expected | Observed | Status |
| :--- | :--- | :--- | :--- | :--- |
| **1. Purchase** | 60 kg Flour @ ₹45/kg -> Qty / Avg / Value | `160 kg` / `₹43.125/kg` / `₹6,900` | `160.000000 kg` / `₹43.125000` / `₹6,900.0000` | **PASS** |
| **2. Production** | Good Murukku 200 g output | `188 packets` | `188.000000 packets` | **PASS** |
| **3. Inventory** | Closing Flour / Oil / Spice / Pouches / Cartons / FG | `120` / `19.5` / `3.8` / `306` / `21` / `238` | `120.0` / `19.5` / `3.8` / `306.0` / `21.0` / `238.0` (`all_reconciled=True`) | **PASS** |
| **4. Variances** | Yield / Oil / Pouch / Carton / Unpacked warning | `-6%` / `+5%` / `-3%` / `-10%` / `8 packets remain unpacked` | `-6.0000%` / `+5.0000%` / `-3.0000%` / `-10.0000%` / `"8 packets remain unpacked"` | **PASS** |
| **5. Order** | Retailer A (TN) 150 pkts -> Admin approval | `APPROVED` | `200 OK` (`APPROVED`) | **PASS** |
| **6. GST Invoice** | Taxable / CGST / SGST / Total + PDF | `₹7,500` / `₹187.50` / `₹187.50` / `₹7,875` | `7500.00` / `187.50` / `187.50` / `7875.00` + valid `%PDF-1.4` | **PASS** |
| **7. Dispatch** | Dispatch 150 pkts -> Closing FG | `88 packets` | `88.000000 packets` | **PASS** |
| **8. Shortage** | Distributor B (KA) 120 vs 88 -> Shortage / IGST / No Invoice | `32` pkts / `IGST ₹300` (`₹6,300`) / Invoice blocked | `32.0` pkts / `igst_preview=300.00`, `total_preview=6300.00` / `AWAITING_STOCK` / Invoice blocked (`409`/`422`) | **PASS** |
| **9. Payment** | Collect `₹4,000` -> Outstanding | `₹3,875` | `total_invoiced=7875.00`, `total_paid=4000.00`, `total_outstanding=3875.00` | **PASS** |
| **10. Costing** | Flour + Oil + Spice + Pouch + Carton + Labour + Gas; Cost/pkt; Profit; Margin | `1725+1470+240+485+135=4055` + `1200+600` = `₹5,855`; `₹31.143617` (`₹31.14`); `₹18.86`; `37.71%` | Exact match across every component (`cost_per_packet_exact ≈ 31.143617`, display `31.14`, profit `18.86`, margin `37.71%`) | **PASS** |

---

## 3. Audit Report, Export, Offline PWA & Security Summary
- **Reports & Exports**: Verified all 15 `/api/v1/reports/*` endpoints cleanly, `reconciled_with_invoices=True`, `reconciled_with_purchases=True`, historical `as_of_date` ledger reconstruction, plus synchronized `.csv`, OOXML `.xlsx`, and `%PDF-1.4` downloads carrying `7875.00` and exact period filters.
- **Schema Integrity**: Verified primary keys, foreign keys, `NUMERIC` precision (zero float degradation), unique constraints (`ix_sales_orders_idempotency_key`, `uq_invoice_fy_sequence`, `uq_invoice_sales_order`), and immutable `StockLedger` SQLAlchemy event listeners.
- **Security Controls**: Tested invalid login (`401`), unauthenticated requests (`401`), cross-salesman isolation (`403`), Auditor write/delete rejection (`403`/`405`), duplicate invoice/dispatch/payment prevention (`409`), negative stock & financial validation (`422`), invalid cross-dimension unit conversion (`422`), and `/orders/sync` per-actor rate limiting (`429`).
- **Offline PWA (`test_phase8_offline_sync.py` & `OfflinePwaSync.test.tsx`)**: Verified idempotent sync (`duplicate: true`), `SUBMITTED` status enforcement, price conflict flagging (`NEEDS_REVIEW`), offline order saving in `offlineDb`, auto-sync on `online` reconnection, retry on failed sync, and logout cache cleanup.

---

## 4. Bugs Discovered & Fixed Across QA & Pre-Deployment Audit
1. **Purchase Register Reconciliation Flag (`backend/app/services/reporting_service.py`)**:
   - *Root Cause*: Early `report_purchase_register` returned `reconciled_with_purchases=True` statically; other report flags (`reconciled_with_ledger`, `reconciled_with_runs`, `reconciled_with_expenses_and_ledger`) also fell back unconditionally to `True` in Phase 7/9.
   - *Fix*: Replaced every unconditional `True` with real SQLAlchemy DB cross-checks (`StockLedger` vs `StockBalance`, `ProductionMaterial` vs `PRODUCTION_ISSUE`, `actual_good_output` vs `PRODUCTION_OUTPUT`, `ProductionExpense` vs costing totals, `Dispatch` vs `SALES_DISPATCH`, `Invoice` lines vs headers, `Purchase` lines vs headers + `PURCHASE_RECEIPT`, and `Payment` vs `PaymentAllocation`). Added `test_report_reconciliations_detect_database_mismatches` confirming each flag returns `False` on injected DB mismatches.
2. **Dedicated Read-Only `OWNER` Role Architecture (`0008_phase10_owner_role`)**:
   - *Root Cause*: `owner@factoryflow.io` previously used `Role.ADMIN` while `Role.OWNER` did not exist as a dedicated read-only role.
   - *Fix*: Added `Role.OWNER = "owner"` across `permissions.py`, `user_service.py`, `dashboard_service.py`, Alembic migration `0008_phase10_owner_role`, and React RBAC (`OwnerRoleDashboard.tsx`, `RoleDashboard.test.tsx`). Verified `OWNER` cannot manage users, approve/create orders/invoices/dispatches, modify purchases/inventory/production, or record payments (`403`).
3. **Async Rendering & Strict Matchers in Frontend Tests**:
   - *Root Cause*: Asynchronous state resolution timing in `OwnerAndAuditReportsPages.test.tsx` (`findAllByText`) and multi-badge rendering in `OfflinePwaSync.test.tsx`.
   - *Fix*: Corrected async queries cleanly in the Vitest suites and enforced strict `Role` typing on `OfflineSessionMeta`.

---

## 5. Automated Suite Totals
- **Backend (`pytest -v`)**: **`89` passed, `0` failed, `0` skipped** (`562.75s`, exit code `0`).
- **Frontend (`vitest run`)**: **`9` test files, `26` passed, `0` failed, `0` skipped** (`49.99s`, exit code `0`, verified on Node `v26.13.1` with JSDOM).
- **Frontend Production Build (`tsc -b && vite build`)**: **Passed** (`1670` modules transformed in `30.50s`, exit code `0`).
- **Total Automated Tests**: **`115` passed, `0` failed, `0` skipped**.

---

## 6. Known Limitations & Remaining Risks
1. **Live PostgreSQL & Neon Execution**: Requires configuring `backend/.env` (`DATABASE_URL` and an isolated `BENCHMARK_TEST_DATABASE_URL`) to run Alembic migrations and the full E2E suite directly against live PostgreSQL.
2. **Browser-Native Testing Scope**: Frontend Vitest executes under JSDOM using mocked API responses and `offlineDb`'s in-memory fallback when `window.indexedDB` is absent; real device/Chromium Playwright offline network-throttling and Android Chrome PWA install tests remain unexecuted locally.
3. **Single-Line Quick Offline Order**: Each offline PWA entry currently stores one product SKU per local order record (supporting multiple separate local orders seamlessly).
