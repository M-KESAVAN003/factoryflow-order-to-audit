export type DatePreset =
  | "today"
  | "yesterday"
  | "last_7_days"
  | "last_30_days"
  | "current_month"
  | "previous_month"
  | "financial_year"
  | "custom"
  | "all";

export interface DateRangeMeta {
  preset: string;
  date_from: string;
  date_to: string;
}

export interface TrendPoint {
  label: string;
  value: string;
  secondary_value: string | null;
}

export interface CategoryValuePoint {
  name: string;
  value: string;
  quantity: string | null;
}

export interface OwnerAlertItem {
  severity: "HIGH" | "MEDIUM";
  category: string;
  message: string;
  reference_id: string | null;
}

export interface OwnerDashboard {
  date_range: DateRangeMeta;
  todays_orders: number;
  pending_orders: number;
  todays_sales: string;
  monthly_sales: string;
  monthly_taxable_revenue: string;
  total_gst_collected: string;
  purchase_value: string;
  production_output: string;
  finished_goods_stock: string;
  raw_material_stock_value: string;
  total_production_cost: string;
  average_cost_per_packet: string;
  gross_margin_pct: string;
  total_customer_receivables: string;
  overdue_receivables: string;
  daily_sales_trend: TrendPoint[];
  monthly_revenue_trend: TrendPoint[];
  product_wise_sales: CategoryValuePoint[];
  customer_wise_sales: CategoryValuePoint[];
  purchase_vs_sales_trend: TrendPoint[];
  production_planned_vs_actual: TrendPoint[];
  material_consumption_comparison: CategoryValuePoint[];
  production_wastage: CategoryValuePoint[];
  cost_per_packet_trend: TrendPoint[];
  outstanding_receivables_trend: TrendPoint[];
  alerts: OwnerAlertItem[];
}

export interface DomainDashboard {
  domain: string;
  date_range: DateRangeMeta;
  metrics: Record<string, string | number>;
}

export interface ReportFilterParams {
  preset?: string;
  date_from?: string;
  date_to?: string;
  month?: string;
  financial_year?: string;
  customer_id?: string;
  product_id?: string;
  supplier_id?: string;
  status?: string;
  category?: string;
  movement_type?: string;
  stock_item_id?: string;
  as_of_date?: string;
  page?: number;
  page_size?: number;
}
