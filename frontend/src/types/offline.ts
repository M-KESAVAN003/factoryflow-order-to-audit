import { Role } from "./auth";
import { SalesOrder, SalesOrderStatus } from "./sales";

export type OfflineSyncStatus =
  | "PENDING_SYNC"
  | "SYNCING"
  | "SYNCED"
  | "SYNC_FAILED"
  | "NEEDS_REVIEW"
  | "CONFLICT";

export type PwaNetworkState =
  | "ONLINE"
  | "OFFLINE"
  | "SYNCING"
  | "PENDING"
  | "SYNC_FAILED";

export interface OfflineSessionMeta {
  key: "active_session";
  userId: string;
  email: string;
  fullName: string;
  department: string;
  role: Role;
  roleDisplayName: string;
  permissions: string[];
  lastAuthenticatedAt: string;
  lastMasterSyncAt: string | null;
}

export interface CachedCustomerMin {
  id: string;
  name: string;
  customer_type: string;
  state: string;
  state_code: string;
  cached_at: string;
}

export interface CachedProductMin {
  id: string;
  name: string;
  sku: string;
  pack_size: string;
  unit_symbol: string;
  selling_price: string;
  gst_rate: string;
  is_active: boolean;
  price_cached_at: string;
}

export interface OfflineOrderRecord {
  localOrderId: string;
  idempotencyKey: string;
  salesmanId: string;
  customerId: string;
  customerName: string;
  customerState: string;
  productId: string;
  productNameSnapshot: string;
  productSku: string;
  unitSymbol: string;
  gstRate: string;
  quantity: string;
  cachedUnitPrice: string;
  cachedPriceTimestamp: string;
  estimatedSubtotal: string;
  estimatedGst: string;
  estimatedTotal: string;
  notes: string | null;
  createdAt: string;
  offlineStatus: "OFFLINE_SAVED";
  syncStatus: OfflineSyncStatus;
  serverOrderId: string | null;
  serverOrderNumber: string | null;
  serverStatus: SalesOrderStatus | null;
  serverUnitPrice: string | null;
  serverTotalAmount: string | null;
  priceConflictNotes: string | null;
  lastSyncAttemptAt: string | null;
  syncedAt: string | null;
  errorMessage: string | null;
  retryCount: number;
}

export interface SalesOrderSyncRequest {
  local_order_id: string;
  idempotency_key: string;
  customer_id: string;
  order_date?: string;
  offline_created_at: string;
  notes?: string | null;
  items: {
    product_id: string;
    product_name_snapshot?: string;
    quantity: string;
    cached_unit_price: string;
    cached_price_timestamp: string;
  }[];
}

export interface PriceConflictLine {
  product_id: string;
  product_name: string;
  submitted_unit_price: string;
  current_server_price: string;
  difference: string;
}

export interface SalesOrderSyncResponse {
  local_order_id: string;
  idempotency_key: string;
  server_order_id: string;
  server_order_number: string;
  server_status: SalesOrderStatus;
  sync_status: "SYNCED" | "NEEDS_REVIEW";
  duplicate: boolean;
  price_review_required: boolean;
  price_conflict_notes: string | null;
  price_conflicts: PriceConflictLine[];
  synced_at: string;
  order: SalesOrder;
}
