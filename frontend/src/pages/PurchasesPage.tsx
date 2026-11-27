import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Download, Eye, Plus } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api, ApiError } from "../lib/api";
import { hasPermission } from "../lib/permissions";
import { Purchase, PurchaseStatus } from "../types/inventoryPurchase";
import { Supplier } from "../types/masterData";
import { PaginationFooter, StatusNotice } from "../components/MasterDataControls";

const PURCHASE_BADGE: Record<PurchaseStatus, string> = {
  DRAFT: "bg-slate-100 text-slate-700",
  REVIEWED: "bg-sky-50 text-sky-700",
  POSTED: "bg-emerald-50 text-emerald-700",
  CANCELLED: "bg-rose-50 text-rose-700",
};

export function PurchasesPage() {
  const { user } = useAuth();
  const canManage = hasPermission(user, "purchases:manage");

  const [purchases, setPurchases] = useState<Purchase[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 15;

  const [search, setSearch] = useState("");
  const [supplierId, setSupplierId] = useState("");
  const [statusFilter, setStatusFilter] = useState<"" | PurchaseStatus>("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadPurchases = async () => {
    setLoading(true);
    setError(null);
    try {
      const [purRes, supRes] = await Promise.all([
        api.listPurchases({
          search: search || undefined,
          supplier_id: supplierId || undefined,
          status: statusFilter === "" ? undefined : statusFilter,
          date_from: dateFrom || undefined,
          date_to: dateTo || undefined,
          page,
          page_size: pageSize,
        }),
        api.listSuppliers({ page_size: 100 }),
      ]);
      setPurchases(purRes.items);
      setTotal(purRes.total);
      setSuppliers(supRes.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load purchase register.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadPurchases();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, supplierId, statusFilter, dateFrom, dateTo, page]);

  const handleExport = async (format: "csv" | "excel" | "pdf") => {
    try {
      const blob = await api.exportPurchases({
        format,
        search: search || undefined,
        supplier_id: supplierId || undefined,
        status: statusFilter === "" ? undefined : statusFilter,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `purchases-register.${format === "excel" ? "xls" : format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Export failed.");
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Purchase Register</h2>
          <p className="text-xs text-slate-500">
            Manage supplier purchases through Draft → Reviewed → Posted with traceable stock receipts.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {(["csv", "excel", "pdf"] as const).map((fmt) => (
            <button
              key={fmt}
              type="button"
              onClick={() => void handleExport(fmt)}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-medium uppercase text-slate-700 hover:bg-slate-50"
            >
              <Download className="h-3.5 w-3.5" /> {fmt}
            </button>
          ))}
          {canManage && (
            <Link
              to="/purchases/new"
              className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3.5 py-2 text-xs font-semibold text-white hover:bg-slate-800"
            >
              <Plus className="h-3.5 w-3.5" /> New Purchase
            </Link>
          )}
        </div>
      </div>

      <StatusNotice error={error} />

      <div className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-5">
        <input
          type="text"
          placeholder="Search reference or supplier..."
          value={search}
          onChange={(e) => {
            setPage(1);
            setSearch(e.target.value);
          }}
          className="rounded-lg border border-slate-300 px-3 py-2 text-xs"
        />
        <select
          aria-label="Filter supplier"
          value={supplierId}
          onChange={(e) => {
            setPage(1);
            setSupplierId(e.target.value);
          }}
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs"
        >
          <option value="">All Suppliers</option>
          {suppliers.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
        <select
          aria-label="Filter purchase status"
          value={statusFilter}
          onChange={(e) => {
            setPage(1);
            setStatusFilter(e.target.value as "" | PurchaseStatus);
          }}
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs"
        >
          <option value="">All Statuses</option>
          <option value="DRAFT">Draft</option>
          <option value="REVIEWED">Reviewed</option>
          <option value="POSTED">Posted</option>
          <option value="CANCELLED">Cancelled</option>
        </select>
        <input
          type="date"
          aria-label="Date from"
          value={dateFrom}
          onChange={(e) => {
            setPage(1);
            setDateFrom(e.target.value);
          }}
          className="rounded-lg border border-slate-300 px-3 py-2 text-xs"
        />
        <input
          type="date"
          aria-label="Date to"
          value={dateTo}
          onChange={(e) => {
            setPage(1);
            setDateTo(e.target.value);
          }}
          className="rounded-lg border border-slate-300 px-3 py-2 text-xs"
        />
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        {loading ? (
          <div className="p-8 text-center text-xs text-slate-500">Loading purchases...</div>
        ) : purchases.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500">No purchase orders found.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Reference</th>
                  <th className="px-4 py-3 font-medium">Supplier</th>
                  <th className="px-4 py-3 font-medium">Date</th>
                  <th className="px-4 py-3 font-medium">Items</th>
                  <th className="px-4 py-3 font-medium">Total (₹)</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Payment</th>
                  <th className="px-4 py-3 font-medium">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {purchases.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-50/70">
                    <td className="px-4 py-3 font-mono font-medium text-slate-900">
                      {p.reference_number}
                    </td>
                    <td className="px-4 py-3 text-slate-700">{p.supplier_name}</td>
                    <td className="px-4 py-3 font-mono text-slate-600">{p.purchase_date}</td>
                    <td className="px-4 py-3 text-slate-600">{p.items.length} line(s)</td>
                    <td className="px-4 py-3 font-mono font-medium text-slate-900">
                      ₹{Number(p.total_amount).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium ${
                          PURCHASE_BADGE[p.status]
                        }`}
                      >
                        {p.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-600">{p.payment_status}</td>
                    <td className="px-4 py-3">
                      <Link
                        to={`/purchases/${p.id}`}
                        className="inline-flex items-center gap-1 rounded border border-slate-200 px-2.5 py-1 text-[11px] font-medium text-slate-700 hover:bg-slate-50"
                      >
                        <Eye className="h-3 w-3" /> Details
                      </Link>
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
