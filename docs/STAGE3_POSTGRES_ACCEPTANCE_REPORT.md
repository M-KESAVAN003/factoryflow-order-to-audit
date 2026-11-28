# FactoryFlow – Order-to-Audit ERP: Stage 3 PostgreSQL Acceptance Report

- **Execution Date:** 2026-11-28
- **Isolated Database Branch:** `factoryflow-test` (endpoint prefix `ep-small-sha`, PostgreSQL `16.16`, database `factoryflow_db`, Alembic head `0008_phase10_owner_role`)
- **Production Database Branch:** `production` (endpoint prefix `ep-quiet-bas`) — **READ-ONLY VERIFIED UNTOUCHED**
- **Code Modifications:** None during initial Stage 3 execution; approved filtered purchase-report fix and tests verified post-Stage-3.

> [!WARNING]
> **Production Security Gate Status: PENDING**
> The Step 1.8 production security gate (rotating the exposed live Neon `production` database password and rotating the Render production `SECRET_KEY` / `JWT_SECRET_KEY`) was waived **exclusively** for this isolated benchmark on `factoryflow-test`. Both production rotations remain **PENDING** before final public handover.

---

## 1. Executive Summary

| Scope / Stage | Result | Notes |
| --- | --- | --- |
| Stage 3 Step 1 – DB Isolation & Safety Guard | **PASS** | `ep-small-sha` vs `ep-quiet-bas`, `SELECT 1 -> 1`, `0008_phase10_owner_role` |
| Stage 3 Step 2 – Reset Safety Guard & Seed Idempotency | **PASS** | Guard blocked `production` env, `DATABASE_URL` match, and DB names without `test`/`benchmark`/`qa`; 2-pass non-destructive seed yielded `0` duplicates |
| Stage 3 Step 3 – Complete 10-Step Manufacturing Benchmark (PostgreSQL) | **PASS** | All inventory, production, variance, costing, GST, dispatch, shortage, and payment assertions passed |
| Stage 3 Step 4 – Row Locking (`FOR UPDATE OF`), Constraints, Rollbacks & RBAC | **PASS** | Exercised `FOR UPDATE OF payments` and `FOR UPDATE OF invoices`; confirmed `409`/`422`/`403` guards and `StockLedger` immutability hook |
| Stage 3 Step 5 – Offline Sync (`/api/v1/orders/sync`) | **PASS** | Synced as `SUBMITTED` without auto-invoice/dispatch; idempotent replay (`duplicate=true`); stale price `45.00` vs `50.00` flagged `NEEDS_REVIEW` |
| Stage 3 Step 6 – Owner Dashboard, 15 Reports, Exports & Audit Trail | **PASS** | Owner + Auditor HTTP `200` on dashboard & all 15 reports; `.csv`, `.xlsx`, `.pdf` contain `7875.00`; `audit_logs_total = 211`; `6/6` stock reconciled |
| Production Database Preservation (`ep-quiet-bas`) | **PASS** | Read-only check confirmed `users=7`, `purchases=1`, `stock_balances=6`, `stock_ledger=7`, `0` test business transactions |
| Production Neon DB Password & Render `SECRET_KEY` Rotation | **PENDING** | Waived strictly for `factoryflow-test`; must still be rotated on live cloud services |
| Physical Android Chrome Mobile PWA Interactive Runtime | **NOT VERIFIED** | Backend offline sync API verified on PostgreSQL; physical Android device Chrome execution not tested in this environment |

---

## 2. Database Safety Guard & Seed Idempotency

### Step 1 – Safety Guard Verification
- Verified `backend/.env.benchmark` exists and is ignored by Git.
- Confirmed `bench_host_prefix = ep-small-sha`, `prod_host_prefix = ep-quiet-bas`, `hosts_differ = true`, and `engine_host_matches_bench = true` after setting process-local `DATABASE_URL` prior to importing `app.*`.
- Live PostgreSQL connection verified on `factoryflow-test`:
  - `SELECT 1` returned `1`
  - `current_database()` returned `factoryflow_db`
  - `alembic_version` returned `['0008_phase10_owner_role']`
  - `version()` returned `PostgreSQL 16.16 (96fad2e) on aarch64-unknown-linux-gnu`

### Step 2 – Reset Safety Guard & Seed Idempotency
- Verified `validate_safe_test_database_url(...)` rejected:
  - `ENVIRONMENT=production` (`SAFETY BLOCK: Refusing to reset/seed when ENVIRONMENT is production.`)
  - URL matching main `DATABASE_URL` (`SAFETY BLOCK: Target URL matches main DATABASE_URL.`)
  - PostgreSQL DB name `factoryflow_db` lacking `'test'`, `'benchmark'`, or `'qa'` (`SAFETY BLOCK: PostgreSQL target database 'factoryflow_db' must contain 'test', 'benchmark', or 'qa'.`)
- Ran double-pass non-destructive seeding (`seed_default_users`, `seed_benchmark_master_data`, `seed_phase3_benchmark_data`, `seed_benchmark_bom`) on `factoryflow-test`:
  - Pass 1 counts equaled Pass 2 counts (`zero_duplicates_pass1_vs_pass2 = true`), with Pass 2 deltas strictly `0` across users, BOMs, benchmark purchases, and master data.

---

## 3. Complete 10-Step Manufacturing Benchmark (Live Neon PostgreSQL)

Executed via FastAPI HTTP endpoints (`TestClient(create_app())`) backed directly by Neon `factoryflow-test`:

| Benchmark Checkpoint | Verified PostgreSQL Result |
| --- | --- |
| Flour Weighted Average (`100 kg @ ₹42` + `60 kg @ ₹45`) | `160.000000 kg` @ `₹43.125000/kg` = `₹6,900.0000` (`BENCHMARK-FLOUR-001` posted) |
| Production Run (`PRD-STAGE3-001`, Planned `1` batch = `200`, Good `188`) | Yield variance `-6.0000%`; Oil variance `+5.0000%`; Pouch variance `-3.0000%` (`188 + 6 damaged`); Carton variance `-10.0000%`; Warning: `"9 cartons hold 180 packets. 188 packets were produced. Therefore, 8 packets remain unpacked."` |
| Post-Production Stock Balances (`reconcile_all = true`) | `RM-FLOUR = 120.000000` (`₹43.125000`), `RM-OIL = 19.500000`, `RM-SPICE = 3.800000`, `PKG-POUCH-200 = 306.000000`, `PKG-CARTON = 21.000000`, Finished Goods `MUR-200 = 238.000000` |
| Production Expenses & Costing (`LABOUR ₹1,200` + `POWER ₹600`) | Raw materials `₹3,435.00` + Packaging `₹620.00` + Overheads `₹1,800.00` = Total `₹5,855.00`; exact cost/packet `₹31.143617` (`₹31.14` display), gross profit/packet `₹18.86`, gross margin `37.71%` |
| Retailer A Intra-State Order (`150` pkts) + GST Invoice + PDF | `INV/2026-27/0001`: Subtotal `₹7,500.00`, CGST `₹187.50`, SGST `₹187.50`, Grand Total `₹7,875.00`; PDF downloaded (`HTTP 200`, `2212` bytes, `%PDF-1.4`) |
| Dispatch (`150` pkts) & Stock Deduction | `MUR-200` dropped `238.000000 -> 88.000000` (valuation `₹1,499.3277` @ `₹17.037815`) |
| Distributor B Inter-State Order (`120` pkts vs `88` available) | Stock check: `all_available = false`, `shortage_quantity = 32.000000`, `tax_type = INTER_STATE`, `igst_preview = ₹300.00`, `total_preview = ₹6,300.00`; order held as `AWAITING_STOCK`; `POST /invoices` & `POST /dispatches` blocked with `422` |
| Payment (`₹4,000.00`) & Receivables | `PAY-STAGE3-RETA-001` (`UTR-STAGE3-PG-001`) created and allocated via `/allocate`: `total_invoiced = ₹7,875.00`, `total_paid = ₹4,000.00`, `total_outstanding = ₹3,875.00`, `reconciled_with_invoices = true` |

---

## 4. PostgreSQL Row Locking, Rollbacks, Duplicates & RBAC

- **PostgreSQL `FOR UPDATE OF` compatibility:** Both initial `POST /api/v1/payments/{id}/allocate` (`₹4,000.00` allocated) and an over-allocation guard check (`₹500.00` rejected with `HTTP 422`) executed `FOR UPDATE OF payments` and `FOR UPDATE OF invoices` against PostgreSQL 16 without SQL errors or deadlocks.
- **Duplicate & validation guards:**
  - Duplicate invoice on already-invoiced order: `HTTP 409`
  - Duplicate dispatch on already-dispatched order: `HTTP 409`
  - Duplicate payment UTR (`UTR-STAGE3-PG-001`): `HTTP 409`
  - Negative stock adjustment (`physical_count = -5`): `HTTP 422`
  - Incompatible dimension unit conversion (`kg -> litre`): `HTTP 422`
- **RBAC isolation:**
  - `salesman_b@factoryflow.io` reading Retailer A's order (`SO-STAGE3-RETA`): `HTTP 403`
  - `owner@factoryflow.io` attempting `POST /api/v1/orders`: `HTTP 403`
  - `auditor@factoryflow.io` attempting `POST /api/v1/inventory/adjustments`: `HTTP 403`
- **Immutability & ledger integrity:** Modifying `StockLedger.quantity_in` raised `ValueError("StockLedger entries are immutable and cannot be modified.")` and rolled back cleanly; `/api/v1/inventory/reconcile` returned `all_reconciled = true` (`checked_items = 6`).

---

## 5. Offline Sync & Conflict Handling

- Valid offline sync (`STAGE3-SYNC-VALID-001`, `cached_unit_price = 50.00`) created an offline order (`is_offline_order = true`, `server_status = SUBMITTED`, `sync_status = SYNCED`, `price_review_required = false`) with `invoice_id = null` and `dispatch_id = null`.
- Idempotent replay of the exact same `idempotency_key` returned `duplicate = true`, `same_order_id = true`, `server_status = SUBMITTED`, creating zero duplicate rows.
- Stale cached price sync (`STAGE3-SYNC-STALE-001`, `cached_unit_price = 45.00` vs server `50.00`) flagged `sync_status = NEEDS_REVIEW`, `price_review_required = true`, populated `price_conflicts` (`difference = 5.00`), and held `server_status = SUBMITTED` with `invoice_id = null` and `dispatch_id = null`.

---

## 6. Owner Dashboard, Reports, Exports & Non-Blocking Findings

- **Owner Dashboard (`/api/v1/dashboard/owner?preset=all`):** `HTTP 200` for both `owner` and `admin`; `finished_goods_stock = 88.000000`, `total_production_cost = 5855.00`, `total_customer_receivables = 3875.00`.
- **All 15 Report Endpoints:** Returned `HTTP 200` for both `auditor@factoryflow.io` and `owner@factoryflow.io`. Stock cut-offs reconciled (`production` report good output `188.000000`, `stock/summary` `MUR-200` total receipts `238.000000`, issues `150.000000`, closing stock `88.000000`).
- **Exports (`/api/v1/reports/export/{csv,excel,pdf}?report_type=sales&preset=all`):**
  - `csv`: `HTTP 200`, `380` bytes, contains `7875.00`
  - `excel`: `HTTP 200`, `2324` bytes, `xl/worksheets/sheet1.xml` contains `7875.00`
  - `pdf`: `HTTP 200`, `1534` bytes, valid `%PDF-1.4` containing `7875.00`
- **Audit Logs:** `GET /api/v1/audit-logs?limit=20` returned `HTTP 200` with `total = 211`.
- **Filtered Purchase Register Observation & Approved Post-Stage-3 Fix:**
  - During the initial baseline Stage 3 run, `/api/v1/reports/purchases?preset=all&stock_item_id=<RM-FLOUR.id>` returned `row_count = 1`, `reconciled_with_purchases = true`, and `posted_total = 0.00` (while unfiltered returned `posted_total = 2700.00`).
  - Following explicit approval, `report_purchase_register` in `backend/app/services/reporting_service.py` was corrected so `stock_item_id`-filtered queries sum matching line amounts (including pro-rata GST) across all rows without pagination bias or `else True` masking, while preserving unfiltered header totals and independent DB header/ledger reconciliation.
  - Re-verified on `factoryflow-test` (`ep-small-sha`) and isolated SQLite: `/api/v1/reports/purchases?preset=all&stock_item_id=<RM-FLOUR.id>` returned `total = 1`, `posted_total = 2700.00`, `reconciled_with_purchases = true`; `RM-OIL` returned `total = 0`, `posted_total = 0.00`; full suites passed (`91/91` backend `pytest`, `26/26` frontend `vitest`, `vite build`). Source edits remain uncommitted locally awaiting final commit/push/redeploy approval.

---

## 7. Production Database Preservation Verification (`ep-quiet-bas`)

Executed a separate read-only SQL count check directly against live `production` (`ep-quiet-bas`) after Stage 3 completion:

| Table | Production Row Count (Post-Benchmark) | Status |
| --- | --- | --- |
| `users` | `7` | Untouched |
| `purchases` | `1` | Untouched |
| `stock_balances` | `6` | Untouched |
| `stock_ledger` | `7` | Untouched |
| `production_runs` | `0` | Untouched |
| `sales_orders` | `0` | Untouched |
| `invoices` | `0` | Untouched |
| `dispatches` | `0` | Untouched |
| `payments` | `0` | Untouched |
