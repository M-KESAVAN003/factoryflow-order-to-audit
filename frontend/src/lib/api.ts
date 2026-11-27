import {
  RoleMatrixResponse,
  TokenResponse,
  UserProfile,
} from "../types/auth";
import {
  AuditLogListResponse,
  RoleDashboardResponse,
  UserListResponse,
  WorkspaceCheckResponse,
} from "../types/dashboard";
import {
  InventoryItemDetail,
  InventoryItemRow,
  InventorySummary,
  MovementType,
  PaymentStatus,
  Purchase,
  PurchaseItemInput,
  PurchaseStatus,
  ReconciliationReport,
  StockAdjustment,
  StockLedgerEntry,
} from "../types/inventoryPurchase";
import {
  Bom,
  BomStatus,
  ProductionDashboard,
  ProductionRun,
  ProductionStatus,
  RunVarianceReport,
  VarianceSummary,
} from "../types/bomProduction";
import {
  CreditNote,
  Dispatch,
  Invoice,
  SalesOrder,
  SalesOrderStatus,
  SalesOrderStockCheck,
  SalesOverview,
} from "../types/sales";
import { SalesOrderSyncRequest, SalesOrderSyncResponse } from "../types/offline";
import {
  CustomerLedger,
  CustomerPayment,
  CustomerPaymentMethod,
  CustomerStatement,
  ExpenseCategory,
  InvoicePaymentsDetail,
  ProductCostSummary,
  ProductionCostDashboard,
  ProductionExpense,
  ReceivablesAgeingReport,
  ReceivablesReport,
  RunCosting,
} from "../types/costingPayment";
import { DomainDashboard, OwnerDashboard, ReportFilterParams } from "../types/reports";
import {
  Customer,
  CustomerType,
  MasterDataSummary,
  PaginatedResponse,
  Product,
  StockItem,
  StockItemType,
  Supplier,
  Unit,
  UnitConversion,
  UnitConvertResponse,
  UnitDimension,
} from "../types/masterData";

const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) || "/api/v1";

const TOKEN_STORAGE_KEY = "factoryflow_access_token";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setStoredToken(token: string | null): void {
  if (token) {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  }
}

function buildQuery(params?: Record<string, string | number | boolean | undefined>): string {
  if (!params) return "";
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") {
      search.set(key, String(value));
    }
  });
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  authenticated = true
): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  if (authenticated) {
    const token = getStoredToken();
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload?.detail) {
        detail = payload.detail;
      }
    } catch {
      // ignore non-JSON error body
    }
    throw new ApiError(response.status, detail);
  }

  return (await response.json()) as T;
}

async function downloadBlob(path: string): Promise<Blob> {
  const headers = new Headers();
  const token = getStoredToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const response = await fetch(`${API_BASE_URL}${path}`, { headers });
  if (!response.ok) {
    throw new ApiError(response.status, `Export failed (${response.status})`);
  }
  return await response.blob();
}

export interface ListQueryParams {
  search?: string;
  is_active?: boolean;
  sort_by?: string;
  sort_dir?: "asc" | "desc";
  page?: number;
  page_size?: number;
}

export const api = {
  health(): Promise<{ status: string; service: string; database: string }> {
    return request("/health", { method: "GET" }, false);
  },

  login(email: string, password: string): Promise<TokenResponse> {
    return request(
      "/auth/login",
      { method: "POST", body: JSON.stringify({ email, password }) },
      false
    );
  },

  logout(): Promise<{ message: string }> {
    return request("/auth/logout", { method: "POST" });
  },

  me(): Promise<UserProfile> {
    return request("/auth/me");
  },

  changePassword(
    current_password: string,
    new_password: string
  ): Promise<{ message: string }> {
    return request("/auth/change-password", {
      method: "POST",
      body: JSON.stringify({ current_password, new_password }),
    });
  },

  roleMatrix(): Promise<RoleMatrixResponse> {
    return request("/auth/roles");
  },

  dashboard(): Promise<RoleDashboardResponse> {
    return request("/dashboard");
  },

  workspaceCheck(
    workspace: "orders" | "production" | "qa"
  ): Promise<WorkspaceCheckResponse> {
    return request(`/workspaces/${workspace}`);
  },

  listUsers(role?: string): Promise<UserListResponse> {
    return request(`/users${buildQuery({ role })}`);
  },

  createUser(payload: {
    email: string;
    full_name: string;
    department: string;
    password: string;
    role: string;
  }): Promise<UserProfile> {
    return request("/users", { method: "POST", body: JSON.stringify(payload) });
  },

  updateUser(
    userId: string,
    payload: {
      full_name?: string;
      department?: string;
      role?: string;
      is_active?: boolean;
    }
  ): Promise<UserProfile> {
    return request(`/users/${userId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },

  listAuditLogs(params?: {
    action?: string;
    actor_role?: string;
    status?: string;
    limit?: number;
  }): Promise<AuditLogListResponse> {
    return request(`/audit-logs${buildQuery(params)}`);
  },

  // Phase 2 Master Data
  masterDataSummary(): Promise<MasterDataSummary> {
    return request("/master-data/summary");
  },

  listProducts(
    params?: ListQueryParams & { category?: string }
  ): Promise<PaginatedResponse<Product>> {
    return request(`/products${buildQuery(params as Record<string, string | number | boolean | undefined>)}`);
  },

  getProduct(id: string): Promise<Product> {
    return request(`/products/${id}`);
  },

  createProduct(payload: Record<string, unknown>): Promise<Product> {
    return request("/products", { method: "POST", body: JSON.stringify(payload) });
  },

  updateProduct(id: string, payload: Record<string, unknown>): Promise<Product> {
    return request(`/products/${id}`, { method: "PUT", body: JSON.stringify(payload) });
  },

  deleteProduct(id: string): Promise<{ status: string; message: string }> {
    return request(`/products/${id}`, { method: "DELETE" });
  },

  listStockItems(
    params?: ListQueryParams & { item_type?: StockItemType }
  ): Promise<PaginatedResponse<StockItem>> {
    return request(`/stock-items${buildQuery(params as Record<string, string | number | boolean | undefined>)}`);
  },

  listRawMaterials(params?: ListQueryParams): Promise<PaginatedResponse<StockItem>> {
    return request(`/raw-materials${buildQuery(params as Record<string, string | number | boolean | undefined>)}`);
  },

  listPackagingMaterials(params?: ListQueryParams): Promise<PaginatedResponse<StockItem>> {
    return request(`/packaging-materials${buildQuery(params as Record<string, string | number | boolean | undefined>)}`);
  },

  getStockItem(id: string): Promise<StockItem> {
    return request(`/stock-items/${id}`);
  },

  createStockItem(payload: Record<string, unknown>): Promise<StockItem> {
    return request("/stock-items", { method: "POST", body: JSON.stringify(payload) });
  },

  updateStockItem(id: string, payload: Record<string, unknown>): Promise<StockItem> {
    return request(`/stock-items/${id}`, { method: "PUT", body: JSON.stringify(payload) });
  },

  listSuppliers(
    params?: ListQueryParams & { state?: string }
  ): Promise<PaginatedResponse<Supplier>> {
    return request(`/suppliers${buildQuery(params as Record<string, string | number | boolean | undefined>)}`);
  },

  getSupplier(id: string): Promise<Supplier> {
    return request(`/suppliers/${id}`);
  },

  createSupplier(payload: Record<string, unknown>): Promise<Supplier> {
    return request("/suppliers", { method: "POST", body: JSON.stringify(payload) });
  },

  updateSupplier(id: string, payload: Record<string, unknown>): Promise<Supplier> {
    return request(`/suppliers/${id}`, { method: "PUT", body: JSON.stringify(payload) });
  },

  listCustomers(
    params?: ListQueryParams & { customer_type?: CustomerType; state?: string }
  ): Promise<PaginatedResponse<Customer>> {
    return request(`/customers${buildQuery(params as Record<string, string | number | boolean | undefined>)}`);
  },

  getCustomer(id: string): Promise<Customer> {
    return request(`/customers/${id}`);
  },

  createCustomer(payload: Record<string, unknown>): Promise<Customer> {
    return request("/customers", { method: "POST", body: JSON.stringify(payload) });
  },

  updateCustomer(id: string, payload: Record<string, unknown>): Promise<Customer> {
    return request(`/customers/${id}`, { method: "PUT", body: JSON.stringify(payload) });
  },

  listUnits(
    params?: ListQueryParams & { dimension?: UnitDimension }
  ): Promise<PaginatedResponse<Unit>> {
    return request(`/units${buildQuery(params as Record<string, string | number | boolean | undefined>)}`);
  },

  createUnit(payload: Record<string, unknown>): Promise<Unit> {
    return request("/units", { method: "POST", body: JSON.stringify(payload) });
  },

  listUnitConversions(params?: {
    product_id?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<UnitConversion>> {
    return request(`/unit-conversions${buildQuery(params as Record<string, string | number | boolean | undefined>)}`);
  },

  createUnitConversion(payload: Record<string, unknown>): Promise<UnitConversion> {
    return request("/unit-conversions", { method: "POST", body: JSON.stringify(payload) });
  },

  convertUnitQuantity(payload: {
    quantity: string;
    from_unit_id: string;
    to_unit_id: string;
    product_id?: string | null;
  }): Promise<UnitConvertResponse> {
    return request("/unit-conversions/convert", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  // Phase 3 Purchases & Inventory
  listPurchases(params?: {
    search?: string;
    supplier_id?: string;
    status?: PurchaseStatus;
    date_from?: string;
    date_to?: string;
    sort_by?: string;
    sort_dir?: "asc" | "desc";
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<Purchase>> {
    return request(`/purchases${buildQuery(params as Record<string, string | number | boolean | undefined>)}`);
  },

  exportPurchases(params: {
    format: "csv" | "excel" | "pdf";
    search?: string;
    supplier_id?: string;
    status?: PurchaseStatus;
    date_from?: string;
    date_to?: string;
  }): Promise<Blob> {
    return downloadBlob(
      `/purchases/export${buildQuery(params as Record<string, string | number | boolean | undefined>)}`
    );
  },

  getPurchase(id: string): Promise<Purchase> {
    return request(`/purchases/${id}`);
  },

  createPurchase(payload: {
    reference_number: string;
    supplier_id: string;
    purchase_date: string;
    payment_status: PaymentStatus;
    notes?: string | null;
    items: PurchaseItemInput[];
  }): Promise<Purchase> {
    return request("/purchases", { method: "POST", body: JSON.stringify(payload) });
  },

  updatePurchase(
    id: string,
    payload: {
      supplier_id?: string;
      purchase_date?: string;
      payment_status?: PaymentStatus;
      status?: PurchaseStatus;
      notes?: string | null;
      items?: PurchaseItemInput[];
    }
  ): Promise<Purchase> {
    return request(`/purchases/${id}`, { method: "PUT", body: JSON.stringify(payload) });
  },

  postPurchase(id: string): Promise<Purchase> {
    return request(`/purchases/${id}/post`, { method: "POST" });
  },

  cancelPurchase(id: string, reason: string): Promise<Purchase> {
    return request(`/purchases/${id}/cancel`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    });
  },

  inventorySummary(): Promise<InventorySummary> {
    return request("/inventory/summary");
  },

  inventoryRawMaterials(
    params?: ListQueryParams & { stock_status?: string }
  ): Promise<PaginatedResponse<InventoryItemRow>> {
    return request(`/inventory/raw-materials${buildQuery(params as Record<string, string | number | boolean | undefined>)}`);
  },

  inventoryPackaging(
    params?: ListQueryParams & { stock_status?: string }
  ): Promise<PaginatedResponse<InventoryItemRow>> {
    return request(`/inventory/packaging${buildQuery(params as Record<string, string | number | boolean | undefined>)}`);
  },

  inventoryFinishedGoods(
    params?: ListQueryParams & { stock_status?: string }
  ): Promise<PaginatedResponse<InventoryItemRow>> {
    return request(`/inventory/finished-goods${buildQuery(params as Record<string, string | number | boolean | undefined>)}`);
  },

  inventoryItemDetail(itemId: string): Promise<InventoryItemDetail> {
    return request(`/inventory/items/${itemId}`);
  },

  reconcileInventory(): Promise<ReconciliationReport> {
    return request("/inventory/reconcile");
  },

  listStockLedger(params?: {
    stock_item_id?: string;
    movement_type?: MovementType;
    reference_doc_id?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<StockLedgerEntry>> {
    return request(`/inventory/ledger${buildQuery(params as Record<string, string | number | boolean | undefined>)}`);
  },

  listAdjustments(params?: {
    stock_item_id?: string;
    status?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<StockAdjustment>> {
    return request(`/inventory/adjustments${buildQuery(params as Record<string, string | number | boolean | undefined>)}`);
  },

  createAdjustment(payload: {
    stock_item_id: string;
    physical_count: string;
    reason: string;
    supporting_notes?: string | null;
    adjustment_date: string;
  }): Promise<StockAdjustment> {
    return request("/inventory/adjustments", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  approveAdjustment(id: string): Promise<StockAdjustment> {
    return request(`/inventory/adjustments/${id}/approve`, { method: "POST" });
  },

  listLowStockAlerts(params?: {
    category?: StockItemType;
    stock_status?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<InventoryItemRow>> {
    return request(`/inventory/alerts${buildQuery(params as Record<string, string | number | boolean | undefined>)}`);
  },

  // Phase 4 BOM & Production
  listBoms(params?: {
    product_id?: string;
    status?: BomStatus;
    is_active?: boolean;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<Bom>> {
    return request(`/boms${buildQuery(params as Record<string, string | number | boolean | undefined>)}`);
  },

  getBom(id: string): Promise<Bom> {
    return request(`/boms/${id}`);
  },

  createBom(payload: {
    product_id: string;
    batch_size: string;
    expected_output: string;
    output_unit_id: string;
    effective_date: string;
    notes?: string | null;
    activate: boolean;
    lines: { stock_item_id: string; standard_quantity: string; unit_id: string }[];
  }): Promise<Bom> {
    return request("/boms", { method: "POST", body: JSON.stringify(payload) });
  },

  updateBom(
    id: string,
    payload: Record<string, unknown>
  ): Promise<Bom> {
    return request(`/boms/${id}`, { method: "PUT", body: JSON.stringify(payload) });
  },

  getBomVersions(id: string): Promise<Bom[]> {
    return request(`/boms/${id}/versions`);
  },

  productionDashboard(): Promise<ProductionDashboard> {
    return request("/production/dashboard");
  },

  varianceSummary(): Promise<VarianceSummary> {
    return request("/production/variance/summary");
  },

  listProductionRuns(params?: {
    search?: string;
    product_id?: string;
    status?: ProductionStatus;
    date_from?: string;
    date_to?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<ProductionRun>> {
    return request(`/production${buildQuery(params as Record<string, string | number | boolean | undefined>)}`);
  },

  getProductionRun(id: string): Promise<ProductionRun> {
    return request(`/production/${id}`);
  },

  createProductionRun(payload: {
    order_number: string;
    product_id: string;
    bom_id?: string | null;
    batch_number: string;
    production_date: string;
    planned_batches: string;
    variance_tolerance_pct?: string;
    notes?: string | null;
  }): Promise<ProductionRun> {
    return request("/production", { method: "POST", body: JSON.stringify(payload) });
  },

  updateProductionRun(id: string, payload: Record<string, unknown>): Promise<ProductionRun> {
    return request(`/production/${id}`, { method: "PUT", body: JSON.stringify(payload) });
  },

  startProductionRun(id: string): Promise<ProductionRun> {
    return request(`/production/${id}/start`, { method: "POST" });
  },

  recordProductionConsumption(
    id: string,
    materials: { stock_item_id: string; actual_quantity: string; damaged_quantity: string }[]
  ): Promise<ProductionRun> {
    return request(`/production/${id}/consume`, {
      method: "POST",
      body: JSON.stringify({ materials }),
    });
  },

  recordProductionOutput(
    id: string,
    payload: { good_quantity: string; damaged_packets: string; cartons_used?: string | null }
  ): Promise<ProductionRun> {
    return request(`/production/${id}/output`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  recordProductionWastage(
    id: string,
    payload: {
      stock_item_id?: string | null;
      wastage_type: string;
      quantity: string;
      unit_id?: string | null;
      reason: string;
      notes?: string | null;
    }
  ): Promise<ProductionRun> {
    return request(`/production/${id}/wastage`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  completeProductionRun(id: string): Promise<ProductionRun> {
    return request(`/production/${id}/complete`, { method: "POST" });
  },

  postProductionRun(id: string): Promise<ProductionRun> {
    return request(`/production/${id}/post`, { method: "POST" });
  },

  cancelProductionRun(id: string, reason: string): Promise<ProductionRun> {
    return request(`/production/${id}/cancel`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    });
  },

  getProductionRunVariance(id: string): Promise<RunVarianceReport> {
    return request(`/production/${id}/variance`);
  },

  // Phase 5 Sales Orders, GST Invoices & Dispatches
  salesOverview(): Promise<SalesOverview> {
    return request("/orders/overview");
  },

  listSalesOrders(params?: {
    search?: string;
    customer_id?: string;
    status?: SalesOrderStatus;
    date_from?: string;
    date_to?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<SalesOrder>> {
    return request(`/orders${buildQuery(params as Record<string, string | number | boolean | undefined>)}`);
  },

  getSalesOrder(id: string): Promise<SalesOrder> {
    return request(`/orders/${id}`);
  },

  createSalesOrder(payload: {
    order_number?: string | null;
    customer_id: string;
    order_date?: string;
    notes?: string | null;
    items: { product_id: string; quantity: string }[];
  }): Promise<SalesOrder> {
    return request("/orders", { method: "POST", body: JSON.stringify(payload) });
  },

  syncOfflineOrder(payload: SalesOrderSyncRequest): Promise<SalesOrderSyncResponse> {
    return request("/orders/sync", { method: "POST", body: JSON.stringify(payload) });
  },

  updateSalesOrder(
    id: string,
    payload: {
      status?: SalesOrderStatus;
      notes?: string | null;
      items?: { product_id: string; quantity: string; unit_price?: string }[];
    }
  ): Promise<SalesOrder> {
    return request(`/orders/${id}`, { method: "PUT", body: JSON.stringify(payload) });
  },

  checkSalesOrderStock(id: string): Promise<SalesOrderStockCheck> {
    return request(`/orders/${id}/stock-check`);
  },

  approveSalesOrder(
    id: string,
    payload?: { hold_if_insufficient?: boolean; allow_partial?: boolean; notes?: string | null }
  ): Promise<SalesOrder> {
    return request(`/orders/${id}/approve`, {
      method: "POST",
      body: JSON.stringify(payload ?? {}),
    });
  },

  rejectSalesOrder(id: string, reason: string): Promise<SalesOrder> {
    return request(`/orders/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    });
  },

  listInvoices(params?: {
    search?: string;
    customer_id?: string;
    financial_year?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<Invoice>> {
    return request(`/invoices${buildQuery(params as Record<string, string | number | boolean | undefined>)}`);
  },

  getInvoice(id: string): Promise<Invoice> {
    return request(`/invoices/${id}`);
  },

  createInvoice(payload: { sales_order_id: string; invoice_date?: string }): Promise<Invoice> {
    return request("/invoices", { method: "POST", body: JSON.stringify(payload) });
  },

  downloadInvoicePdf(id: string): Promise<Blob> {
    return downloadBlob(`/invoices/${id}/pdf`);
  },

  issueCreditNote(
    invoiceId: string,
    payload: { reason: string; amount?: string; credit_date?: string }
  ): Promise<CreditNote> {
    return request(`/invoices/${invoiceId}/credit-notes`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  listDispatches(params?: {
    search?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<Dispatch>> {
    return request(`/dispatches${buildQuery(params as Record<string, string | number | boolean | undefined>)}`);
  },

  getDispatch(id: string): Promise<Dispatch> {
    return request(`/dispatches/${id}`);
  },

  createDispatch(payload: {
    sales_order_id: string;
    dispatch_date?: string;
    vehicle_number?: string | null;
    transporter_name?: string | null;
    notes?: string | null;
  }): Promise<Dispatch> {
    return request("/dispatches", { method: "POST", body: JSON.stringify(payload) });
  },

  // Phase 6 Production Costing, Expenses, Payments & Receivables
  productionCostDashboard(product_id?: string): Promise<ProductionCostDashboard> {
    return request(`/costing/production${buildQuery({ product_id })}`);
  },

  runCosting(runId: string): Promise<RunCosting> {
    return request(`/costing/production/${runId}`);
  },

  productCosting(productId: string): Promise<ProductCostSummary> {
    return request(`/costing/products/${productId}`);
  },

  listRunExpenses(runId: string): Promise<ProductionExpense[]> {
    return request(`/production/${runId}/expenses`);
  },

  addRunExpense(
    runId: string,
    payload: {
      category: ExpenseCategory;
      description: string;
      amount: string;
      expense_date?: string;
      auto_post?: boolean;
    }
  ): Promise<ProductionExpense> {
    return request(`/production/${runId}/expenses`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  updateRunExpense(
    runId: string,
    expenseId: string,
    payload: {
      category?: ExpenseCategory;
      description?: string;
      amount?: string;
      expense_date?: string;
    }
  ): Promise<ProductionExpense> {
    return request(`/production/${runId}/expenses/${expenseId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  },

  postRunExpense(runId: string, expenseId: string): Promise<ProductionExpense> {
    return request(`/production/${runId}/expenses/${expenseId}/post`, { method: "POST" });
  },

  reverseRunExpense(runId: string, expenseId: string): Promise<ProductionExpense> {
    return request(`/production/${runId}/expenses/${expenseId}/reverse`, { method: "POST" });
  },

  listPayments(params?: {
    search?: string;
    customer_id?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<CustomerPayment>> {
    return request(`/payments${buildQuery(params as Record<string, string | number | boolean | undefined>)}`);
  },

  getPayment(id: string): Promise<CustomerPayment> {
    return request(`/payments/${id}`);
  },

  createPayment(payload: {
    payment_reference?: string | null;
    customer_id: string;
    payment_date?: string;
    payment_method: CustomerPaymentMethod;
    amount_received: string;
    transaction_reference?: string | null;
    notes?: string | null;
    allocations?: { invoice_id: string; amount: string; notes?: string }[];
  }): Promise<CustomerPayment> {
    return request("/payments", { method: "POST", body: JSON.stringify(payload) });
  },

  allocatePayment(
    paymentId: string,
    payload: {
      allocation_date?: string;
      allocations: { invoice_id: string; amount: string; notes?: string }[];
    }
  ): Promise<CustomerPayment> {
    return request(`/payments/${paymentId}/allocate`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  invoicePayments(invoiceId: string): Promise<InvoicePaymentsDetail> {
    return request(`/invoices/${invoiceId}/payments`);
  },

  receivablesReport(params?: {
    customer_id?: string;
    as_of_date?: string;
  }): Promise<ReceivablesReport> {
    return request(`/receivables${buildQuery(params as Record<string, string | number | boolean | undefined>)}`);
  },

  receivablesAgeing(params?: {
    customer_id?: string;
    as_of_date?: string;
  }): Promise<ReceivablesAgeingReport> {
    return request(`/receivables/ageing${buildQuery(params as Record<string, string | number | boolean | undefined>)}`);
  },

  customerLedger(customerId: string): Promise<CustomerLedger> {
    return request(`/customers/${customerId}/ledger`);
  },

  customerStatement(
    customerId: string,
    params?: { from_date?: string; to_date?: string }
  ): Promise<CustomerStatement> {
    return request(`/customers/${customerId}/statement${buildQuery(params as Record<string, string | number | boolean | undefined>)}`);
  },

  // Phase 7 Owner Dashboard, Audit Reports & Multi-Format Exports
  ownerDashboard(params?: ReportFilterParams): Promise<OwnerDashboard> {
    return request(`/dashboard/owner${buildQuery(params as Record<string, string | number | boolean | undefined>)}`);
  },

  domainDashboard(
    domain: "sales" | "production" | "inventory" | "finance",
    params?: ReportFilterParams
  ): Promise<DomainDashboard> {
    return request(`/dashboard/${domain}${buildQuery(params as Record<string, string | number | boolean | undefined>)}`);
  },

  fetchReport<T = Record<string, unknown>>(
    endpoint: string,
    params?: ReportFilterParams
  ): Promise<T> {
    return request(`/reports/${endpoint}${buildQuery(params as Record<string, string | number | boolean | undefined>)}`);
  },

  exportReport(
    format: "excel" | "csv" | "pdf",
    reportType: string,
    params?: ReportFilterParams
  ): Promise<Blob> {
    return downloadBlob(
      `/reports/export/${format}${buildQuery({
        report_type: reportType,
        ...(params ?? {}),
      } as Record<string, string | number | boolean | undefined>)}`
    );
  },
};
