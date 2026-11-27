import { StockItemType } from "./masterData";

export type BomStatus = "DRAFT" | "ACTIVE" | "INACTIVE";
export type ProductionStatus =
  | "DRAFT"
  | "PLANNED"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "POSTED"
  | "CANCELLED";

export interface BomLine {
  id: string;
  stock_item_id: string;
  stock_item_name: string;
  stock_item_sku: string;
  input_category: StockItemType;
  standard_quantity: string;
  unit_id: string;
  unit_symbol: string;
  base_quantity: string;
  base_unit_symbol: string;
  available_stock: string;
}

export interface Bom {
  id: string;
  product_id: string;
  product_name: string;
  product_sku: string;
  version_number: number;
  batch_size: string;
  expected_output: string;
  output_unit_id: string;
  output_unit_symbol: string;
  effective_date: string;
  status: BomStatus;
  is_active: boolean;
  notes: string | null;
  created_by_email: string;
  created_at: string;
  updated_at: string;
  lines: BomLine[];
}

export interface ProductionMaterial {
  id: string;
  stock_item_id: string;
  stock_item_name: string;
  stock_item_sku: string;
  input_category: StockItemType;
  unit_id: string;
  unit_symbol: string;
  base_unit_symbol: string;
  planned_quantity: string;
  planned_base_quantity: string;
  actual_quantity: string;
  damaged_quantity: string;
  total_consumed_base_qty: string;
  available_stock: string;
  insufficient_stock: boolean;
  difference_qty: string;
  variance_pct: string | null;
  variance_status: "GREEN" | "ORANGE" | "RED" | null;
  exceeds_tolerance: boolean;
}

export interface ProductionOutput {
  id: string;
  product_id: string;
  unit_symbol: string;
  expected_quantity: string;
  good_quantity: string;
  damaged_packets: string;
  cartons_used: string;
  carton_capacity_packets: string;
  unpacked_packets: string;
  packaging_warning: string | null;
  recorded_by_email: string;
  recorded_at: string;
}

export interface ProductionWastage {
  id: string;
  stock_item_id: string | null;
  stock_item_name: string | null;
  wastage_type: string;
  quantity: string;
  unit_symbol: string | null;
  reason: string;
  notes: string | null;
  recorded_by_email: string;
  created_at: string;
}

export interface ProductionRun {
  id: string;
  order_number: string;
  product_id: string;
  product_name: string;
  product_sku: string;
  bom_id: string;
  bom_version_snapshot: number;
  batch_number: string;
  production_date: string;
  planned_batches: string;
  expected_output: string;
  actual_good_output: string;
  damaged_packets: string;
  damaged_pouches: string;
  scrap_quantity: string;
  yield_variance_pct: string | null;
  yield_status: "GREEN" | "ORANGE" | "RED";
  yield_exceeds_tolerance: boolean;
  variance_tolerance_pct: string;
  packaging_warning: string | null;
  supervisor_id: string;
  supervisor_email: string;
  notes: string | null;
  status: ProductionStatus;
  started_at: string | null;
  completed_at: string | null;
  posted_at: string | null;
  created_at: string;
  materials: ProductionMaterial[];
  outputs: ProductionOutput[];
  wastages: ProductionWastage[];
}

export interface MaterialVarianceRow {
  stock_item_id: string;
  material_name: string;
  sku: string;
  input_category: StockItemType;
  unit_symbol: string;
  planned_consumption: string;
  actual_consumption: string;
  damaged_quantity: string;
  difference: string;
  variance_pct: string;
  status: "GREEN" | "ORANGE" | "RED";
  exceeds_tolerance: boolean;
}

export interface RunVarianceReport {
  production_run_id: string;
  order_number: string;
  product_name: string;
  tolerance_pct: string;
  expected_output: string;
  actual_good_output: string;
  yield_variance_pct: string;
  yield_status: "GREEN" | "ORANGE" | "RED";
  yield_exceeds_tolerance: boolean;
  packaging_warning: string | null;
  materials: MaterialVarianceRow[];
}

export interface VarianceSummaryItem {
  production_run_id: string;
  order_number: string;
  product_name: string;
  production_date: string;
  status: ProductionStatus;
  expected_output: string;
  actual_good_output: string;
  yield_variance_pct: string;
  yield_status: "GREEN" | "ORANGE" | "RED";
  flagged_material_count: number;
}

export interface VarianceSummary {
  total_runs: number;
  flagged_runs: number;
  avg_yield_variance_pct: string;
  runs: VarianceSummaryItem[];
}

export interface ProductionDashboard {
  todays_runs: number;
  planned_output: string;
  actual_output: string;
  total_wastage: string;
  overall_yield_variance_pct: string;
  pending_runs: number;
  active_boms: number;
  daily_trend: {
    date: string;
    planned_output: string;
    actual_output: string;
    wastage: string;
  }[];
  product_yield: {
    product_name: string;
    runs_count: number;
    expected_output: string;
    actual_output: string;
    yield_pct: string;
  }[];
  recent_runs: ProductionRun[];
  variance_alerts: VarianceSummaryItem[];
}
