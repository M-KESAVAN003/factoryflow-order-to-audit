import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../lib/api";
import { InventoryItemRow } from "../types/inventoryPurchase";
import { StockItemType } from "../types/masterData";
import { StatusNotice } from "../components/MasterDataControls";

const ALERT_BADGE: Record<InventoryItemRow["stock_status"], string> = {
  GREEN: "bg-emerald-50 text-emerald-700 border-emerald-200",
  ORANGE: "bg-amber-50 text-amber-800 border-amber-200",
  RED: "bg-rose-50 text-rose-700 border-rose-200",
};

const ALERT_LABEL: Record<InventoryItemRow["stock_status"], string> = {
  GREEN: "Sufficient (Green)",
  ORANGE: "Approaching Reorder (Orange)",
  RED: "Below Reorder (Red)",
};

export function LowStockAlertsPage() {
  const [items, setItems] = useState<InventoryItemRow[]>([]);
  const [category, setCategory] = useState<"" | StockItemType>("");
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await api.listLowStockAlerts({
          category: category === "" ? undefined : category,
          stock_status: statusFilter || undefined,
          page_size: 100,
        });
        setItems(res.items);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load alerts.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [category, statusFilter]);

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">Low Stock Alerts</h2>
        <p className="text-xs text-slate-500">
          Reorder threshold monitoring across Raw Materials, Packaging Materials, and Finished Goods.
        </p>
      </div>

      <StatusNotice error={error} />

      <div className="flex flex-wrap gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <select
          aria-label="Filter by category"
          value={category}
          onChange={(e) => setCategory(e.target.value as "" | StockItemType)}
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs"
        >
          <option value="">All Categories</option>
          <option value="RAW_MATERIAL">Raw Materials</option>
          <option value="PACKAGING">Packaging Materials</option>
          <option value="FINISHED_GOOD">Finished Goods</option>
        </select>

        <select
          aria-label="Filter by alert status"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs"
        >
          <option value="">All Alert Levels</option>
          <option value="RED">Below Reorder (Red)</option>
          <option value="ORANGE">Approaching Reorder (Orange)</option>
          <option value="GREEN">Sufficient (Green)</option>
        </select>
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        {loading ? (
          <div className="p-8 text-center text-xs text-slate-500">Checking reorder thresholds...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Item</th>
                  <th className="px-4 py-3 font-medium">Category</th>
                  <th className="px-4 py-3 font-medium">Available Stock</th>
                  <th className="px-4 py-3 font-medium">Reorder Level</th>
                  <th className="px-4 py-3 font-medium">Shortage Qty</th>
                  <th className="px-4 py-3 font-medium">Alert Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {items.map((item) => (
                  <tr key={item.stock_item_id} className="hover:bg-slate-50/70">
                    <td className="px-4 py-3">
                      <Link
                        to={`/inventory/items/${item.stock_item_id}`}
                        className="font-medium text-sky-700 hover:underline"
                      >
                        {item.name}
                      </Link>
                      <div className="font-mono text-[11px] text-slate-400">{item.sku}</div>
                    </td>
                    <td className="px-4 py-3 text-slate-600">{item.category_label}</td>
                    <td className="px-4 py-3 font-mono font-medium text-slate-900">
                      {Number(item.available_quantity)} {item.base_unit_symbol}
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-700">
                      {Number(item.reorder_level)} {item.base_unit_symbol}
                    </td>
                    <td className="px-4 py-3 font-mono text-rose-700">
                      {Number(item.shortage_quantity) > 0
                        ? `${Number(item.shortage_quantity)} ${item.base_unit_symbol}`
                        : "0"}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded-md border px-2.5 py-0.5 text-[11px] font-medium ${
                          ALERT_BADGE[item.stock_status]
                        }`}
                      >
                        {ALERT_LABEL[item.stock_status]}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
