# FactoryFlow Phase 8 – Offline PWA & Automatic Order Synchronization

FactoryFlow provides an installable, offline-capable Progressive Web App (PWA) for field salesmen operating in weak or zero-connectivity environments, while keeping FastAPI + PostgreSQL strictly authoritative.

## 1. PWA Configuration
- **Manifest**: `frontend/public/manifest.webmanifest` (`display: "standalone"`, `start_url: "/sales/dashboard"`, 192×192 & 512×512 PNG icons).
- **Icons**: `frontend/public/icons/icon-192.png` and `frontend/public/icons/icon-512.png`.
- **Service Worker**: `frontend/public/sw.js` registered by `frontend/src/lib/pwa.ts`.
  - Pre-caches the offline application shell (`/`, `/index.html`, `/manifest.webmanifest`, icons) and static assets via stale-while-revalidate.
  - Falls back to cached `/index.html` for offline SPA route navigation.
  - **Security rule**: Never caches `/api/*` requests in CacheStorage (`network-only`).
  - Dispatches version update prompts (`SKIP_WAITING`) surfaced in `NetworkStatusBanner`.
- **HTTPS Requirement**: Service Workers and Android Chrome PWA installation require HTTPS in production (`localhost` / `127.0.0.1` permitted during local development).

## 2. Installation on Mobile Browsers
1. Open FactoryFlow in Chrome/Edge on Android (or desktop Chromium) over HTTPS.
2. When eligible, click **Install PWA** in the header banner (captured via `beforeinstallprompt`) or choose **Install app / Add to Home screen** from the browser menu.
3. Launch FactoryFlow from the home-screen icon in standalone mode.

## 3. Offline Storage Policy (IndexedDB)
Database: `factoryflow_offline_db` (version `1`), implemented in `frontend/src/lib/offlineDb.ts`:
- `session_meta`: non-sensitive active profile metadata (`userId`, `email`, `fullName`, `role`, `permissions`, `lastAuthenticatedAt`, `lastMasterSyncAt`). **No passwords and no JWT secrets are stored in IndexedDB.**
- `customers_cache`: minimal active assigned customer fields (`id`, `name`, `customer_type`, `state`, `state_code`, `cached_at`).
- `products_cache`: minimal active product catalog + cached selling price & `price_cached_at`.
- `offline_orders`: structured local queue indexed by `localOrderId` (keyPath), `syncStatus`, `salesmanId`, and unique `idempotencyKey`.

**Logout Policy**: Calling **Sign out** clears the session token, `session_meta`, `customers_cache`, `products_cache`, and already-`SYNCED` local history so personal customer data is not exposed after logout.

## 4. Synchronization Process & Idempotency
1. While online, click **Sync Catalog** to cache assigned customers and active products with timestamped prices.
2. While offline, open **Offline Order (PWA)** (`/sales/offline-order`), select customer + active cached product, verify cached price timestamp, and click **Save Order Locally (Pending Sync)**.
3. Synchronization triggers automatically:
   - On application launch if pending orders exist and `navigator.onLine` is true.
   - Immediately upon browser `online` reconnection events.
   - Via Background Sync (`factoryflow-order-sync` tag) when supported by Chromium browsers, falling back cleanly to foreground synchronization.
   - Manually via **Sync Now** or **Retry Sync**.
4. **Endpoint**: `POST /api/v1/orders/sync`
   - Requires authenticated `SALES_ORDERS_CREATE` permission (`ADMIN` or `ORDER_MANAGER`).
   - Enforces per-actor sliding-window rate limiting (`120` requests / `60s`).
   - Validates customer assignment, active customer/product status, and positive quantities.
   - Enforces PostgreSQL unique constraint on `sales_orders.idempotency_key` (`0007_phase8_offline_sync`): replays with the same key return the existing `SalesOrder` (`duplicate: true`) rather than creating duplicates.
   - Creates orders strictly in `SUBMITTED` status — never `APPROVED`, `INVOICED`, or `DISPATCHED` — and never reserves or deducts inventory offline.

## 5. Price Conflict Handling
- Each offline order line submits `cached_unit_price` and `cached_price_timestamp`.
- On sync, the server preserves the salesman's snapshot in `sales_order_items.submitted_unit_price` and compares it against current `Product.selling_price`.
- If the server price changed while offline:
  - `SalesOrder.price_review_required = true` and `price_conflict_notes` lists the cached vs current price difference.
  - Local order transitions to **Needs Review**; Admin sees a **Price Review Required** warning banner in `AdminOrdersDashboardPage` and `OrderApprovalPage` before approval.

## 6. Order Sync Statuses & Network States
- **Order Statuses**: `Pending Sync`, `Syncing`, `Synced`, `Sync Failed`, `Needs Review`, `Conflict`.
- **Network Indicator States**:
  - `Online – Connected`
  - `Offline – No Internet`
  - `Syncing – Uploading Orders`
  - `Pending – Orders Waiting`
  - `Sync Failed – Action Required`

## 7. Browser Compatibility & Known Limitations
- **Full Background Sync (`SyncManager`)**: Supported mainly on Android/Desktop Chrome & Edge. Safari/iOS and Firefox fall back reliably to launch-time + `online`-event + manual foreground synchronization.
- **Offline Auth Window**: Requires an online login beforehand and an unexpired client token for subsequent automatic sync; if a server returns `401 Unauthorized` upon reconnection, the user must sign in again while failed/unsynced orders remain safely preserved.
- **No Offline Stock Promise**: Finished-goods availability is verified only by Admin on the backend prior to approval and dispatch.

## 8. Verification & Testing Steps
- Backend: `cd backend && .\.venv\Scripts\python.exe -m pytest -v tests/test_phase8_offline_sync.py`
- Frontend: `cd frontend && npm test` (`OfflinePwaSync.test.tsx`) and `npm run build`
