export type SalesOrderStatus =
  | "SUBMITTED"
  | "UNDER_REVIEW"
  | "APPROVED"
  | "AWAITING_STOCK"
  | "PARTIALLY_FULFILLED"
  | "INVOICED"
  | "DISPATCHED"
  | "REJECTED"
  | "CANCELLED";

export type TaxType = "INTRA_STATE" | "INTER_STATE";

export interface SalesOrderItem {
  id: string;
  product_id: string;
  product_name: string;
  sku: string;
  pack_size: string;
  hsn_code: string;
  unit_symbol: string;
  requested_quantity: string;
  approved_quantity: string;
  dispatched_quantity: string;
  unit_price: string;
  submitted_unit_price?: string | null;
  gst_rate: string;
  taxable_value: string;
  cgst_rate: string;
  sgst_rate: string;
  igst_rate: string;
  cgst_amount: string;
  sgst_amount: string;
  igst_amount: string;
  line_total: string;
  available_stock: string;
  shortage_quantity: string;
}

export interface SalesOrder {
  id: string;
  order_number: string;
  customer_id: string;
  customer_name: string;
  customer_type: string;
  customer_gstin: string;
  salesman_id: string;
  salesman_name: string;
  salesman_email: string;
  order_date: string;
  status: SalesOrderStatus;
  factory_state: string;
  customer_state: string;
  place_of_supply: string;
  tax_type: TaxType;
  subtotal: string;
  cgst_amount: string;
  sgst_amount: string;
  igst_amount: string;
  tax_amount: string;
  total_amount: string;
  has_stock_shortage: boolean;
  shortage_notes: string | null;
  notes: string | null;
  rejection_reason: string | null;
  invoice_id: string | null;
  invoice_number: string | null;
  dispatch_id: string | null;
  dispatch_number: string | null;
  idempotency_key?: string | null;
  local_order_id?: string | null;
  is_offline_order?: boolean;
  offline_created_at?: string | null;
  synced_at?: string | null;
  price_review_required?: boolean;
  price_conflict_notes?: string | null;
  created_at: string;
  updated_at: string;
  items: SalesOrderItem[];
}

export interface StockCheckLine {
  product_id: string;
  product_name: string;
  sku: string;
  unit_symbol: string;
  requested_quantity: string;
  available_stock: string;
  committed_stock: string;
  net_available_stock: string;
  shortage_quantity: string;
  sufficient: boolean;
}

export interface SalesOrderStockCheck {
  sales_order_id: string;
  order_number: string;
  status: SalesOrderStatus;
  tax_type: TaxType;
  all_available: boolean;
  recommended_action: string;
  subtotal_preview: string;
  cgst_preview: string;
  sgst_preview: string;
  igst_preview: string;
  total_preview: string;
  lines: StockCheckLine[];
}

export interface CreditNote {
  id: string;
  credit_note_number: string;
  invoice_id: string;
  financial_year: string;
  credit_date: string;
  reason: string;
  amount: string;
  created_by_email: string;
  created_at: string;
}

export interface InvoiceItem {
  id: string;
  product_id: string;
  product_name: string;
  sku: string;
  pack_size: string;
  hsn_code: string;
  unit_symbol: string;
  quantity: string;
  unit_price: string;
  gst_rate: string;
  taxable_value: string;
  cgst_rate: string;
  sgst_rate: string;
  igst_rate: string;
  cgst_amount: string;
  sgst_amount: string;
  igst_amount: string;
  line_total: string;
}

export interface Invoice {
  id: string;
  invoice_number: string;
  financial_year: string;
  sequence_number: number;
  sales_order_id: string;
  order_number: string;
  customer_id: string;
  invoice_date: string;
  status: "POSTED";
  factory_name: string;
  factory_address: string;
  factory_gstin: string;
  factory_state: string;
  factory_state_code: string;
  customer_name: string;
  customer_gstin: string;
  billing_address: string;
  customer_state: string;
  place_of_supply: string;
  tax_type: TaxType;
  subtotal: string;
  cgst_amount: string;
  sgst_amount: string;
  igst_amount: string;
  tax_amount: string;
  grand_total: string;
  amount_in_words: string;
  created_by_email: string;
  created_at: string;
  dispatch_id: string | null;
  dispatch_number: string | null;
  items: InvoiceItem[];
  credit_notes: CreditNote[];
}

export interface DispatchItem {
  id: string;
  product_id: string;
  product_name: string;
  sku: string;
  stock_item_id: string;
  quantity: string;
  stock_ledger_id: string;
}

export interface Dispatch {
  id: string;
  dispatch_number: string;
  sales_order_id: string;
  order_number: string;
  invoice_id: string;
  invoice_number: string;
  customer_name: string;
  dispatch_date: string;
  vehicle_number: string | null;
  transporter_name: string | null;
  notes: string | null;
  dispatched_by_email: string;
  created_at: string;
  items: DispatchItem[];
}

export interface CustomerSalesSummaryRow {
  customer_id: string;
  customer_name: string;
  customer_type: string;
  customer_state: string;
  orders_count: number;
  dispatched_count: number;
  total_order_value: string;
  invoiced_value: string;
}

export interface SalesOverview {
  total_orders: number;
  pending_review: number;
  awaiting_stock: number;
  invoiced_count: number;
  dispatched_count: number;
  total_sales_value: string;
  total_gst_collected: string;
  customer_summary: CustomerSalesSummaryRow[];
}
