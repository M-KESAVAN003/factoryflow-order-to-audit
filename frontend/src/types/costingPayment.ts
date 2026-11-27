export type ExpenseCategory =
  | "LABOUR"
  | "GAS"
  | "ELECTRICITY"
  | "POWER"
  | "MAINTENANCE"
  | "OTHER_OVERHEAD";

export type ExpenseStatus = "DRAFT" | "POSTED" | "REVERSED";

export type CustomerPaymentMethod = "CASH" | "BANK_TRANSFER" | "UPI" | "CHEQUE" | "OTHER";

export type CustomerPaymentStatus = "DRAFT" | "POSTED" | "REVERSED";

export interface ProductionExpense {
  id: string;
  expense_number: string;
  production_run_id: string;
  order_number: string;
  category: ExpenseCategory;
  description: string;
  amount: string;
  expense_date: string;
  status: ExpenseStatus;
  reversal_of_id: string | null;
  recorded_by_email: string;
  posted_at: string | null;
  created_at: string;
}

export interface MaterialCostLine {
  stock_item_id: string;
  stock_item_name: string;
  sku: string;
  category: string;
  actual_quantity: string;
  damaged_quantity: string;
  total_consumed_qty: string;
  unit_symbol: string;
  weighted_avg_rate: string;
  total_cost: string;
}

export interface RunCosting {
  production_run_id: string;
  order_number: string;
  batch_number: string;
  product_id: string;
  product_name: string;
  product_sku: string;
  production_date: string;
  status: string;
  actual_good_output: string;
  unit_symbol: string;
  raw_material_cost: string;
  packaging_cost: string;
  material_and_packaging_cost: string;
  labour_cost: string;
  gas_and_power_cost: string;
  other_overhead_cost: string;
  total_overhead_cost: string;
  total_production_cost: string;
  cost_per_packet_exact: string;
  cost_per_packet_display: string;
  selling_price_before_gst: string;
  gross_profit_per_packet: string;
  gross_margin_pct: string;
  materials: MaterialCostLine[];
  expenses: ProductionExpense[];
}

export interface ProductCostSummary {
  product_id: string;
  product_name: string;
  product_sku: string;
  runs_count: number;
  total_good_output: string;
  total_material_cost: string;
  total_expense_cost: string;
  total_production_cost: string;
  avg_cost_per_packet: string;
  selling_price_before_gst: string;
  gross_profit_per_packet: string;
  gross_margin_pct: string;
  runs: RunCosting[];
}

export interface ProductionCostDashboard {
  total_runs_costed: number;
  total_good_output: string;
  total_raw_material_cost: string;
  total_packaging_cost: string;
  total_labour_cost: string;
  total_gas_and_power_cost: string;
  total_other_overhead_cost: string;
  total_production_cost: string;
  avg_cost_per_packet: string;
  avg_gross_margin_pct: string;
  products: ProductCostSummary[];
  runs: RunCosting[];
}

export interface PaymentAllocation {
  id: string;
  payment_id: string;
  payment_reference: string;
  invoice_id: string;
  invoice_number: string;
  allocated_amount: string;
  allocation_date: string;
  notes: string | null;
  allocated_by_email: string;
  created_at: string;
}

export interface CustomerPayment {
  id: string;
  payment_reference: string;
  customer_id: string;
  customer_name: string;
  payment_date: string;
  payment_method: CustomerPaymentMethod;
  amount_received: string;
  allocated_amount: string;
  unallocated_advance: string;
  transaction_reference: string | null;
  notes: string | null;
  status: CustomerPaymentStatus;
  recorded_by_email: string;
  created_at: string;
  allocations: PaymentAllocation[];
}

export interface InvoicePaymentStatusRow {
  invoice_id: string;
  invoice_number: string;
  customer_id: string;
  customer_name: string;
  invoice_date: string;
  due_date: string;
  invoice_amount: string;
  paid_amount: string;
  credit_note_amount: string;
  outstanding_amount: string;
  payment_status: "UNPAID" | "PARTIAL" | "PAID";
  days_overdue: number;
  ageing_category: string;
}

export interface InvoicePaymentsDetail {
  invoice: InvoicePaymentStatusRow;
  allocations: PaymentAllocation[];
}

export interface CustomerReceivableSummary {
  customer_id: string;
  customer_name: string;
  customer_state: string;
  invoices_count: number;
  total_invoiced: string;
  total_paid: string;
  unallocated_advance: string;
  total_outstanding: string;
  net_receivable: string;
}

export interface ReceivablesReport {
  total_invoiced: string;
  total_collected: string;
  total_unallocated_advances: string;
  total_outstanding: string;
  default_payment_term_days: number;
  customers: CustomerReceivableSummary[];
  invoices: InvoicePaymentStatusRow[];
}

export interface AgeingBucketSummary {
  category: string;
  invoices_count: number;
  outstanding_amount: string;
}

export interface ReceivablesAgeingReport {
  as_of_date: string;
  default_payment_term_days: number;
  total_outstanding: string;
  buckets: AgeingBucketSummary[];
  rows: InvoicePaymentStatusRow[];
}

export interface CustomerLedgerEntry {
  entry_date: string;
  doc_type: string;
  reference_number: string;
  description: string;
  debit_amount: string;
  credit_amount: string;
  running_balance: string;
}

export interface CustomerLedger {
  customer_id: string;
  customer_name: string;
  customer_gstin: string;
  customer_state: string;
  total_invoiced: string;
  total_paid: string;
  unallocated_advance: string;
  closing_outstanding: string;
  entries: CustomerLedgerEntry[];
}

export interface CustomerStatement {
  customer_id: string;
  customer_name: string;
  customer_gstin: string;
  billing_address: string;
  from_date: string | null;
  to_date: string | null;
  opening_balance: string;
  period_debits: string;
  period_credits: string;
  closing_balance: string;
  unallocated_advance: string;
  invoices: InvoicePaymentStatusRow[];
  entries: CustomerLedgerEntry[];
}
