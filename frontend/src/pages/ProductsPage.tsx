import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Edit2, Plus, Trash2 } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api, ApiError } from "../lib/api";
import { hasPermission } from "../lib/permissions";
import { Product } from "../types/masterData";
import {
  ConfirmDialog,
  MasterFilterBar,
  PaginationFooter,
  StatusNotice,
} from "../components/MasterDataControls";

export function ProductsPage() {
  const { user } = useAuth();
  const canManage = hasPermission(user, "products:manage");

  const [items, setItems] = useState<Product[]>([]);
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
  const [deleteTarget, setDeleteTarget] = useState<Product | null>(null);

  const loadProducts = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listProducts({
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
      setError(err instanceof ApiError ? err.message : "Failed to load products.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadProducts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, statusFilter, sortBy, sortDir, page]);

  const handleConfirmDelete = async () => {
    if (!deleteTarget) return;
    setError(null);
    setSuccess(null);
    try {
      const res = await api.deleteProduct(deleteTarget.id);
      setSuccess(res.message);
      setDeleteTarget(null);
      await loadProducts();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to delete product.");
      setDeleteTarget(null);
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Finished Products</h2>
          <p className="text-xs text-slate-500">
            Sellable products linked 1:1 to FINISHED_GOOD StockItem records.
          </p>
        </div>
        {canManage && (
          <Link
            to="/products/new"
            className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3.5 py-2 text-xs font-semibold text-white hover:bg-slate-800"
          >
            <Plus className="h-3.5 w-3.5" /> Add Product
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
        searchPlaceholder="Search product name, SKU, or HSN..."
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
          { value: "selling_price", label: "Selling Price" },
          { value: "created_at", label: "Created" },
        ]}
        sortDir={sortDir}
        onSortDirChange={setSortDir}
      />

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        {loading ? (
          <div className="p-8 text-center text-xs text-slate-500">Loading products...</div>
        ) : items.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500">No products found.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Product</th>
                  <th className="px-4 py-3 font-medium">SKU</th>
                  <th className="px-4 py-3 font-medium">Pack / Unit</th>
                  <th className="px-4 py-3 font-medium">Price (₹)</th>
                  <th className="px-4 py-3 font-medium">GST / HSN</th>
                  <th className="px-4 py-3 font-medium">Carton Config</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  {canManage && <th className="px-4 py-3 font-medium">Actions</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {items.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-50/70">
                    <td className="px-4 py-3">
                      <div className="font-medium text-slate-900">{p.name}</div>
                      <div className="text-[11px] text-slate-500">{p.category}</div>
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-800">{p.sku}</td>
                    <td className="px-4 py-3 text-slate-600">
                      {p.pack_size} ({p.unit_symbol})
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-900">
                      ₹{Number(p.selling_price).toFixed(2)}
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      {p.gst_rate}% &bull; <span className="font-mono">{p.hsn_code}</span>
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      {p.packets_per_carton} pkts/carton
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium ${
                          p.is_active
                            ? "bg-emerald-50 text-emerald-700"
                            : "bg-slate-100 text-slate-500"
                        }`}
                      >
                        {p.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    {canManage && (
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <Link
                            to={`/products/${p.id}/edit`}
                            className="inline-flex items-center gap-1 rounded border border-slate-200 px-2 py-1 text-[11px] font-medium text-slate-700 hover:bg-slate-50"
                          >
                            <Edit2 className="h-3 w-3" /> Edit
                          </Link>
                          <button
                            type="button"
                            onClick={() => setDeleteTarget(p)}
                            className="inline-flex items-center gap-1 rounded border border-rose-200 px-2 py-1 text-[11px] font-medium text-rose-700 hover:bg-rose-50"
                          >
                            <Trash2 className="h-3 w-3" /> Remove
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
        open={deleteTarget !== null}
        title="Remove or Deactivate Product"
        message={`Proceed with removing "${deleteTarget?.name ?? ""}"? If referenced by unit conversions or transactions, it will be safely deactivated instead of deleted.`}
        confirmLabel="Confirm"
        onConfirm={() => void handleConfirmDelete()}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
