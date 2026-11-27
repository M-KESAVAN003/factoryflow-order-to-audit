import { StockItemType } from "./masterData";

export type PurchaseStatus = "DRAFT" | "REVIEWED" | "POSTED" | "CANCELLED";
export type PaymentStatus = "UNPAID" | "PARTIAL" | "PAID";
export type AdjustmentStatus = "PENDING" | "APPROVED";

export type MovementType =
  | "OPENING_STOCK"
  | "PURCHASE_RECEIPT"
  | "PRODUCTION_ISSUE"
  | "PRODUCTION_OUTPUT"
  | "SALES_DISPATCH"
  | "SALES_RETURN"
  | "PURCHASE_RETURN"
  | "STOCK_ADJUSTMENT"
  | "REVERSAL";

export interface PurchaseItemInput {
  stock_item_id: string;
  unit_id: string;
  quantity: string;
  unit_rate: string;
  tax_rate: string;
}

export interface PurchaseItem {
  id: string;
  stock_item_id: string;
  stock_item_name: string;
  stock_item_sku: string;
  unit_id: string;
  unit_symbol: string;
  base_unit_symbol: string;
  quantity: string;
  base_quantity: string;
  unit_rate: string;
  tax_rate: string;
  tax_amount: string;
  line_subtotal: string;
  line_total: string;
}

export interface Purchase {
  id: string;
  reference_number: string;
  supplier_id: string;
  supplier_name: string;
  purchase_date: string;
  status: PurchaseStatus;
  payment_status: PaymentStatus;
  subtotal: string;
  tax_amount: string;
  total_amount: string;
  notes: string | null;
  created_by: string;
  created_by_email: string;
  posted_by: string | null;
  posted_at: string | null;
  cancelled_at: string | null;
  cancel_reason: string | null;
  created_at: string;
  updated_at: string;
  items: PurchaseItem[];
}

export interface InventoryItemRow {
  stock_item_id: string;
  name: string;
  sku: string;
  item_type: StockItemType;
  category_label: string;
  base_unit_id: string;
  base_unit_symbol: string;
  available_quantity: string;
  average_cost: string;
  stock_value: string;
  reorder_level: string;
  shortage_quantity: string;
  stock_status: "GREEN" | "ORANGE" | "RED";
  is_active: boolean;
  last_movement_at: string | null;
}

export interface StockLedgerEntry {
  id: string;
  stock_item_id: string;
  stock_item_name: string;
  stock_item_sku: string;
  movement_type: MovementType;
  quantity_in: string;
  quantity_out: string;
  base_unit_symbol: string;
  reference_doc_type: string;
  reference_doc_id: string;
  transaction_date: string;
  unit_cost: string;
  total_value: string;
  balance_qty_after: string;
  avg_cost_after: string;
  balance_value_after: string;
  notes: string | null;
  created_by_email: string | null;
  created_at: string;
}

export interface InventoryItemDetail {
  item: InventoryItemRow;
  ledger_sum_quantity: string;
  reconciled: boolean;
  recent_movements: StockLedgerEntry[];
}

export interface CategorySummary {
  item_type: StockItemType;
  label: string;
  item_count: number;
  total_quantity: string;
  total_value: string;
  low_stock_count: number;
}

export interface InventorySummary {
  total_items: number;
  total_stock_value: string;
  low_stock_red_count: number;
  approaching_orange_count: number;
  categories: CategorySummary[];
  recent_movements: StockLedgerEntry[];
}

export interface StockAdjustment {
  id: string;
  stock_item_id: string;
  stock_item_name: string;
  stock_item_sku: string;
  base_unit_symbol: string;
  current_balance: string;
  physical_count: string;
  difference: string;
  reason: string;
  supporting_notes: string | null;
  status: AdjustmentStatus;
  adjustment_date: string;
  created_by_email: string;
  approved_by_email: string | null;
  approved_at: string | null;
  created_at: string;
}

export interface ReconciliationReport {
  all_reconciled: boolean;
  checked_items: number;
  items: {
    stock_item_id: string;
    sku: string;
    name: string;
    balance_quantity: string;
    ledger_quantity: string;
    discrepancy: string;
    reconciled: boolean;
  }[];
}
