import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AppRoutes } from "../App";
import { AuthProvider } from "../context/AuthContext";
import { api, setStoredToken } from "../lib/api";
import { Role, UserProfile } from "../types/auth";
import {
  clearOfflineCachesOnLogout,
  getCachedCustomers,
  getCachedProducts,
  getSessionMeta,
  listOfflineOrders,
  resetInMemoryOfflineFallbackForTests,
  saveCachedCustomers,
  saveCachedProducts,
  saveSessionMeta,
} from "../lib/offlineDb";
import { registerFactoryFlowServiceWorker } from "../lib/pwa";

const SALESMAN_PROFILE: UserProfile = {
  id: "salesman-1",
  email: "orders@factoryflow.io",
  full_name: "Marcus Chen",
  department: "Planning & Orders",
  role: "order_manager" as Role,
  role_display_name: "Order & Production Manager",
  is_active: true,
  permissions: [
    "dashboard:view",
    "roles:read",
    "products:read",
    "customers:read",
    "units:read",
    "sales_orders:read",
    "sales_orders:create",
  ],
  created_at: "2026-11-27T00:00:00Z",
  last_login_at: null,
};

function setNavigatorOnline(online: boolean) {
  Object.defineProperty(window.navigator, "onLine", {
    configurable: true,
    value: online,
  });
}

describe("Phase 8 Offline PWA & Automatic Order Synchronization", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    resetInMemoryOfflineFallbackForTests();
    localStorage.clear();
    setNavigatorOnline(true);
  });

  it("registers service worker and links PWA manifest cleanly", async () => {
    const mockReg = {
      waiting: null,
      installing: null,
      addEventListener: vi.fn(),
    } as unknown as ServiceWorkerRegistration;
    const registerSpy = vi.fn().mockResolvedValue(mockReg);
    Object.defineProperty(window.navigator, "serviceWorker", {
      configurable: true,
      value: {
        register: registerSpy,
        addEventListener: vi.fn(),
        ready: Promise.resolve(mockReg),
      },
    });
    const reg = await registerFactoryFlowServiceWorker();
    expect(registerSpy).toHaveBeenCalledWith("/sw.js", { scope: "/" });
    expect(reg).toBe(mockReg);
  });

  it("loads offline PWA shell when disconnected, stores multiple orders in IndexedDB, and clears caches on logout", async () => {
    setStoredToken("cached-salesman-jwt");
    setNavigatorOnline(false);

    vi.spyOn(api, "me").mockRejectedValue(new TypeError("Failed to fetch"));
    await saveSessionMeta({
      key: "active_session",
      userId: SALESMAN_PROFILE.id,
      email: SALESMAN_PROFILE.email,
      fullName: SALESMAN_PROFILE.full_name,
      department: SALESMAN_PROFILE.department,
      role: SALESMAN_PROFILE.role,
      roleDisplayName: SALESMAN_PROFILE.role_display_name,
      permissions: SALESMAN_PROFILE.permissions,
      lastAuthenticatedAt: "2026-11-27T08:00:00Z",
      lastMasterSyncAt: "2026-11-27T08:01:00Z",
    });
    await saveCachedCustomers([
      {
        id: "cust-ret-a",
        name: "Retailer A",
        customer_type: "RETAILER",
        state: "Tamil Nadu",
        state_code: "33",
        cached_at: "2026-11-27T08:01:00Z",
      },
    ]);
    await saveCachedProducts([
      {
        id: "prod-mur",
        name: "Murukku 200 g",
        sku: "MUR-200",
        pack_size: "200 g",
        unit_symbol: "packet",
        selling_price: "50.00",
        gst_rate: "5.00",
        is_active: true,
        price_cached_at: "2026-11-27T08:01:00Z",
      },
    ]);

    render(
      <MemoryRouter initialEntries={["/sales/offline-order"]}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    );

    expect(
      await screen.findByRole("heading", { name: "Offline Order Entry (PWA)" })
    ).toBeInTheDocument();
    expect(screen.getByTestId("network-status-pill")).toHaveTextContent("Offline – No Internet");

    const user = userEvent.setup();
    const saveBtn = screen.getByRole("button", { name: /Save Order Locally/i });
    await user.click(saveBtn);
    expect(await screen.findByText(/Saved locally:/i)).toBeInTheDocument();
    expect(screen.getAllByText("Pending Sync").length).toBeGreaterThanOrEqual(1);

    await user.click(saveBtn);
    const saved = await listOfflineOrders(SALESMAN_PROFILE.id);
    expect(saved).toHaveLength(2);
    expect(saved[0].idempotencyKey).not.toBe(saved[1].idempotencyKey);
    expect(saved.every((o) => o.syncStatus === "PENDING_SYNC")).toBe(true);

    // Explicit logout clears session meta, cached customers & cached products
    vi.spyOn(api, "logout").mockResolvedValue({ message: "ok" });
    await user.click(screen.getByRole("button", { name: /Sign out/i }));
    await waitFor(async () => {
      expect(await getSessionMeta()).toBeNull();
      expect(await getCachedCustomers()).toEqual([]);
      expect(await getCachedProducts()).toEqual([]);
    });
  });

  it("auto-syncs pending offline orders on reconnection, handles price review and failed retry", async () => {
    setStoredToken("valid-salesman-jwt");
    setNavigatorOnline(false);

    vi.spyOn(api, "me").mockResolvedValue(SALESMAN_PROFILE);
    await saveSessionMeta({
      key: "active_session",
      userId: SALESMAN_PROFILE.id,
      email: SALESMAN_PROFILE.email,
      fullName: SALESMAN_PROFILE.full_name,
      department: SALESMAN_PROFILE.department,
      role: SALESMAN_PROFILE.role,
      roleDisplayName: SALESMAN_PROFILE.role_display_name,
      permissions: SALESMAN_PROFILE.permissions,
      lastAuthenticatedAt: "2026-11-27T08:00:00Z",
      lastMasterSyncAt: "2026-11-27T08:01:00Z",
    });
    await saveCachedCustomers([
      {
        id: "cust-ret-a",
        name: "Retailer A",
        customer_type: "RETAILER",
        state: "Tamil Nadu",
        state_code: "33",
        cached_at: "2026-11-27T08:01:00Z",
      },
    ]);
    await saveCachedProducts([
      {
        id: "prod-mur",
        name: "Murukku 200 g",
        sku: "MUR-200",
        pack_size: "200 g",
        unit_symbol: "packet",
        selling_price: "50.00",
        gst_rate: "5.00",
        is_active: true,
        price_cached_at: "2026-11-27T08:01:00Z",
      },
    ]);

    const syncSpy = vi
      .spyOn(api, "syncOfflineOrder")
      .mockRejectedValueOnce(new Error("Temporary server error"))
      .mockResolvedValueOnce({
        local_order_id: "LOC-1",
        idempotency_key: "key-1",
        server_order_id: "srv-order-1",
        server_order_number: "SO-2026-0009",
        server_status: "SUBMITTED",
        sync_status: "NEEDS_REVIEW",
        duplicate: false,
        price_review_required: true,
        price_conflict_notes: "Murukku 200 g: cached offline Rs 50.00 vs current server Rs 55.00",
        price_conflicts: [
          {
            product_id: "prod-mur",
            product_name: "Murukku 200 g",
            submitted_unit_price: "50.00",
            current_server_price: "55.00",
            difference: "5.00",
          },
        ],
        synced_at: "2026-11-27T09:00:00Z",
        order: {
          id: "srv-order-1",
          order_number: "SO-2026-0009",
          customer_id: "cust-ret-a",
          customer_name: "Retailer A",
          customer_type: "RETAILER",
          customer_gstin: "33RETLA0001A1Z5",
          salesman_id: "salesman-1",
          salesman_name: "Marcus Chen",
          salesman_email: "orders@factoryflow.io",
          order_date: "2026-11-27",
          status: "SUBMITTED",
          factory_state: "Tamil Nadu",
          customer_state: "Tamil Nadu",
          place_of_supply: "Tamil Nadu (33)",
          tax_type: "INTRA_STATE",
          subtotal: "8250.00",
          cgst_amount: "206.25",
          sgst_amount: "206.25",
          igst_amount: "0.00",
          tax_amount: "412.50",
          total_amount: "8662.50",
          has_stock_shortage: false,
          shortage_notes: null,
          notes: null,
          rejection_reason: null,
          invoice_id: null,
          invoice_number: null,
          dispatch_id: null,
          dispatch_number: null,
          created_at: "2026-11-27T09:00:00Z",
          updated_at: "2026-11-27T09:00:00Z",
          items: [
            {
              id: "item-1",
              product_id: "prod-mur",
              product_name: "Murukku 200 g",
              sku: "MUR-200",
              pack_size: "200 g",
              hsn_code: "19059090",
              unit_symbol: "packet",
              requested_quantity: "150",
              approved_quantity: "150",
              dispatched_quantity: "0",
              unit_price: "55.00",
              submitted_unit_price: "50.00",
              gst_rate: "5.00",
              taxable_value: "8250.00",
              cgst_rate: "2.50",
              sgst_rate: "2.50",
              igst_rate: "0.00",
              cgst_amount: "206.25",
              sgst_amount: "206.25",
              igst_amount: "0.00",
              line_total: "8662.50",
              available_stock: "0",
              shortage_quantity: "150",
            },
          ],
        },
      });

    render(
      <MemoryRouter initialEntries={["/sales/offline-order"]}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    );

    const user = userEvent.setup();
    await screen.findByRole("heading", { name: "Offline Order Entry (PWA)" });
    await user.click(screen.getByRole("button", { name: /Save Order Locally/i }));
    await screen.findByText(/Saved locally:/i);

    // Reconnect network -> auto-sync runs, first call fails -> Sync Failed
    setNavigatorOnline(true);
    fireEvent(window, new Event("online"));

    await waitFor(() => {
      expect(syncSpy).toHaveBeenCalledTimes(1);
    });
    expect(await screen.findByTestId("network-status-pill")).toHaveTextContent(
      "Sync Failed – Action Required"
    );

    // Navigate to Failed Orders & retry -> succeeds with Needs Review (price conflict)
    await user.click(screen.getByRole("link", { name: /Failed & Conflicts/i }));
    expect(await screen.findByText(/Temporary server error/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Retry Sync/i }));
    await waitFor(() => {
      expect(syncSpy).toHaveBeenCalledTimes(2);
    });
    expect(await screen.findByText(/SO-2026-0009/i)).toBeInTheDocument();
    expect(screen.getByText("Needs Review")).toBeInTheDocument();

    await clearOfflineCachesOnLogout();
  });
});
