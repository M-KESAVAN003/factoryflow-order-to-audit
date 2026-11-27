export type UnitDimension = "mass" | "volume" | "count";
export type StockItemType = "RAW_MATERIAL" | "PACKAGING" | "FINISHED_GOOD";
export type CustomerType = "Retailer" | "Distributor";

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface Unit {
  id: string;
  name: string;
  symbol: string;
  dimension: UnitDimension;
  is_base: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface UnitConversion {
  id: string;
  from_unit_id: string;
  from_unit_symbol: string;
  from_unit_dimension: UnitDimension;
  to_unit_id: string;
  to_unit_symbol: string;
  to_unit_dimension: UnitDimension;
  product_id: string | null;
  product_name: string | null;
  conversion_factor: string;
  is_active: boolean;
  created_at: string;
}

export interface UnitConvertResponse {
  input_quantity: string;
  converted_quantity: string;
  from_unit_symbol: string;
  to_unit_symbol: string;
  factor_applied: string;
}

export interface StockItem {
  id: string;
  name: string;
  sku: string;
  item_type: StockItemType;
  base_unit_id: string;
  base_unit_symbol: string;
  purchase_unit_id: string;
  purchase_unit_symbol: string;
  purchase_rate: string;
  reorder_level: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Product {
  id: string;
  name: string;
  sku: string;
  category: string;
  description: string | null;
  pack_size: string;
  selling_price: string;
  gst_rate: string;
  hsn_code: string;
  unit_id: string;
  unit_symbol: string;
  stock_item_id: string;
  stock_item_sku: string;
  stock_item_type: StockItemType;
  pouch_stock_item_id: string | null;
  pouch_stock_item_name: string | null;
  carton_stock_item_id: string | null;
  carton_stock_item_name: string | null;
  packets_per_carton: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Supplier {
  id: string;
  name: string;
  gstin: string;
  phone: string;
  email: string | null;
  address: string;
  state: string;
  state_code: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Customer {
  id: string;
  name: string;
  customer_type: CustomerType;
  gstin: string;
  phone: string;
  address: string;
  city: string;
  state: string;
  state_code: string;
  assigned_salesman_id: string | null;
  assigned_salesman_name: string | null;
  credit_limit: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface MasterDataSummary {
  products_total: number;
  products_active: number;
  raw_materials_total: number;
  packaging_materials_total: number;
  suppliers_total: number;
  customers_total: number;
  units_total: number;
  conversions_total: number;
}
