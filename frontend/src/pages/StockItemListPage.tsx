import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Edit2, Plus, Power } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api, ApiError } from "../lib/api";
import { hasPermission } from "../lib/permissions";
import { StockItem, StockItemType } from "../types/masterData";
import {
  ConfirmDialog,
  MasterFilterBar,
  PaginationFooter,
  StatusNotice,
} from "../components/MasterDataControls";

export function StockItemListPage({
  itemType,
  title,
  subtitle,
  basePath,
}: {
  itemType: Extract<StockItemType, "RAW_MATERIAL" | "PACKAGING">;
  title: string;
  subtitle: string;
  basePath: string;
}) {
  const { user } = useAuth();
  const canManage = hasPermission(user, "stock_items:manage");

  const [items, setItems] = useState<StockItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 10;

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [sortBy, setSortBy] = useState("name");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [toggleTarget, setToggleTarget] = useState<StockItem | null>(null);

  const loadItems = async () => {
    setLoading(true);
    setError(null);
    try {
      const fetcher =
        itemType === "RAW_MATERIAL"
          ? api.listRawMaterials
          : api.listPackagingMaterials;
      const res = await fetcher({
        search: search || undefined,
        is_active: statusFilter === "" ? undefined : statusFilter === "true",
        sort_by: sortBy,
        sort_dir: sortDir,
        page,
        page_size: pageSize,
      });
      setItems(res.items);
      setTotal(res.total);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : `Failed to load ${title.toLowerCase()}.`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadItems();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [itemType, search, statusFilter, sortBy, sortDir, page]);

  const handleConfirmToggle = async () => {
    if (!toggleTarget) return;
    try {
      const updated = await api.updateStockItem(toggleTarget.id, {
        is_active: !toggleTarget.is_active,
      });
      setSuccess(
        `${updated.name} (${updated.sku}) is now ${updated.is_active ? "Active" : "Inactive"}.`
      );
      setToggleTarget(null);
      await loadItems();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update item status.");
      setToggleTarget(null);
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
          <p className="text-xs text-slate-500">{subtitle}</p>
        </div>
        {canManage && (
          <Link
            to={`${basePath}/new`}
            className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3.5 py-2 text-xs font-semibold text-white hover:bg-slate-800"
          >
            <Plus className="h-3.5 w-3.5" /> Add {itemType === "RAW_MATERIAL" ? "Raw Material" : "Packaging"}
          </Link>
        )}
      </div>

      <StatusNotice error={error} success={success} />

      <MasterFilterBar
        search={search}
        onSearchChange={(v) => {
          setPage(1);
          setSearch(v);
        }}
        searchPlaceholder="Search item name or SKU..."
        statusFilter={statusFilter}
        onStatusFilterChange={(v) => {
          setPage(1);
          setStatusFilter(v);
        }}
        sortBy={sortBy}
        onSortByChange={setSortBy}
        sortOptions={[
          { value: "name", label: "Name" },
          { value: "sku", label: "SKU" },
          { value: "purchase_rate", label: "Purchase Rate" },
        ]}
        sortDir={sortDir}
        onSortDirChange={setSortDir}
      />

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        {loading ? (
          <div className="p-8 text-center text-xs text-slate-500">Loading items...</div>
        ) : items.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500">No items found.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Item Name</th>
                  <th className="px-4 py-3 font-medium">SKU</th>
                  <th className="px-4 py-3 font-medium">Base / Purchase Unit</th>
                  <th className="px-4 py-3 font-medium">Purchase Rate (₹)</th>
                  <th className="px-4 py-3 font-medium">Reorder Level</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  {canManage && <th className="px-4 py-3 font-medium">Actions</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {items.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50/70">
                    <td className="px-4 py-3">
                      <div className="font-medium text-slate-900">{item.name}</div>
                      {item.description && (
                        <div className="text-[11px] text-slate-500">{item.description}</div>
                      )}
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-800">{item.sku}</td>
                    <td className="px-4 py-3 text-slate-600">
                      {item.base_unit_symbol} / {item.purchase_unit_symbol}
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-900">
                      ₹{Number(item.purchase_rate).toFixed(2)}
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-600">
                      {Number(item.reorder_level).toFixed(2)} {item.base_unit_symbol}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium ${
                          item.is_active
                            ? "bg-emerald-50 text-emerald-700"
                            : "bg-slate-100 text-slate-500"
                        }`}
                      >
                        {item.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    {canManage && (
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <Link
                            to={`${basePath}/${item.id}/edit`}
                            className="inline-flex items-center gap-1 rounded border border-slate-200 px-2 py-1 text-[11px] font-medium text-slate-700 hover:bg-slate-50"
                          >
                            <Edit2 className="h-3 w-3" /> Edit
                          </Link>
                          <button
                            type="button"
                            onClick={() => setToggleTarget(item)}
                            className="inline-flex items-center gap-1 rounded border border-slate-200 px-2 py-1 text-[11px] font-medium text-slate-700 hover:bg-slate-50"
                          >
                            <Power className="h-3 w-3" />
                            {item.is_active ? "Deactivate" : "Activate"}
                          </button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <PaginationFooter page={page} pageSize={pageSize} total={total} onPageChange={setPage} />
      </div>

      <ConfirmDialog
        open={toggleTarget !== null}
        title={toggleTarget?.is_active ? "Deactivate Stock Item" : "Activate Stock Item"}
        message={`Confirm changing active status for "${toggleTarget?.name ?? ""}"?`}
        confirmLabel="Confirm"
        onConfirm={() => void handleConfirmToggle()}
        onCancel={() => setToggleTarget(null)}
      />
    </div>
  );
}
