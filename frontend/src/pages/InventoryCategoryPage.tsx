import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../lib/api";
import { InventoryItemRow } from "../types/inventoryPurchase";
import {
  MasterFilterBar,
  PaginationFooter,
  StatusNotice,
} from "../components/MasterDataControls";

const STATUS_BADGE: Record<InventoryItemRow["stock_status"], string> = {
  GREEN: "bg-emerald-50 text-emerald-700 border-emerald-200",
  ORANGE: "bg-amber-50 text-amber-800 border-amber-200",
  RED: "bg-rose-50 text-rose-700 border-rose-200",
};

export function InventoryCategoryPage({
  category,
  title,
  subtitle,
}: {
  category: "RAW_MATERIAL" | "PACKAGING" | "FINISHED_GOOD";
  title: string;
  subtitle: string;
}) {
  const [items, setItems] = useState<InventoryItemRow[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 15;

  const [search, setSearch] = useState("");
  const [stockStatusFilter, setStockStatusFilter] = useState("");
  const [sortBy, setSortBy] = useState("name");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const fetcher =
        category === "RAW_MATERIAL"
          ? api.inventoryRawMaterials
          : category === "PACKAGING"
          ? api.inventoryPackaging
          : api.inventoryFinishedGoods;
      const res = await fetcher({
        search: search || undefined,
        stock_status: stockStatusFilter || undefined,
        sort_by: sortBy,
        sort_dir: sortDir,
        page,
        page_size: pageSize,
      });
      setItems(res.items);
      setTotal(res.total);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load inventory.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [category, search, stockStatusFilter, sortBy, sortDir, page]);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
          <p className="text-xs text-slate-500">{subtitle}</p>
        </div>
        <Link
          to="/inventory"
          className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          ← Inventory Overview
        </Link>
      </div>

      <StatusNotice error={error} />

      <MasterFilterBar
        search={search}
        onSearchChange={(v) => {
          setPage(1);
          setSearch(v);
        }}
        searchPlaceholder="Search item name or SKU..."
        sortBy={sortBy}
        onSortByChange={setSortBy}
        sortOptions={[
          { value: "name", label: "Name" },
          { value: "sku", label: "SKU" },
          { value: "available_quantity", label: "Available Qty" },
          { value: "stock_value", label: "Stock Value" },
        ]}
        sortDir={sortDir}
        onSortDirChange={setSortDir}
        extraFilter={
          <select
            aria-label="Filter by stock status"
            value={stockStatusFilter}
            onChange={(e) => {
              setPage(1);
              setStockStatusFilter(e.target.value);
            }}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs focus:border-slate-900 focus:outline-none"
          >
            <option value="">All Stock Statuses</option>
            <option value="GREEN">Sufficient (Green)</option>
            <option value="ORANGE">Approaching Reorder (Orange)</option>
            <option value="RED">Below Reorder (Red)</option>
          </select>
        }
      />

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        {loading ? (
          <div className="p-8 text-center text-xs text-slate-500">Loading inventory...</div>
        ) : items.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500">No items matched filters.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Item</th>
                  <th className="px-4 py-3 font-medium">SKU</th>
                  <th className="px-4 py-3 font-medium">Available Qty</th>
                  <th className="px-4 py-3 font-medium">Avg Cost (₹)</th>
                  <th className="px-4 py-3 font-medium">Stock Value (₹)</th>
                  <th className="px-4 py-3 font-medium">Reorder Level</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {items.map((row) => (
                  <tr key={row.stock_item_id} className="hover:bg-slate-50/70">
                    <td className="px-4 py-3">
                      <Link
                        to={`/inventory/items/${row.stock_item_id}`}
                        className="font-medium text-sky-700 hover:underline"
                      >
                        {row.name}
                      </Link>
                      <div className="text-[11px] text-slate-500">{row.category_label}</div>
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-800">{row.sku}</td>
                    <td className="px-4 py-3 font-mono font-medium text-slate-900">
                      {Number(row.available_quantity)} {row.base_unit_symbol}
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-700">
                      ₹{Number(row.average_cost).toFixed(3)}
                    </td>
                    <td className="px-4 py-3 font-mono font-medium text-slate-900">
                      ₹{Number(row.stock_value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-600">
                      {Number(row.reorder_level)} {row.base_unit_symbol}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded-md border px-2 py-0.5 text-[11px] font-medium ${
                          STATUS_BADGE[row.stock_status]
                        }`}
                      >
                        {row.stock_status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <PaginationFooter page={page} pageSize={pageSize} total={total} onPageChange={setPage} />
      </div>
    </div>
  );
}
