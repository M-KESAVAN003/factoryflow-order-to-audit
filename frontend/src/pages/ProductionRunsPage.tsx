import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Eye, Plus } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api, ApiError } from "../lib/api";
import { hasPermission } from "../lib/permissions";
import { ProductionRun, ProductionStatus } from "../types/bomProduction";
import { PaginationFooter, StatusNotice } from "../components/MasterDataControls";

const STATUS_BADGE: Record<ProductionStatus, string> = {
  DRAFT: "bg-slate-100 text-slate-700",
  PLANNED: "bg-sky-50 text-sky-700",
  IN_PROGRESS: "bg-amber-50 text-amber-800",
  COMPLETED: "bg-indigo-50 text-indigo-700",
  POSTED: "bg-emerald-50 text-emerald-700",
  CANCELLED: "bg-rose-50 text-rose-700",
};

export function ProductionRunsPage() {
  const { user } = useAuth();
  const canManage = hasPermission(user, "production_runs:manage");

  const [runs, setRuns] = useState<ProductionRun[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 15;

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"" | ProductionStatus>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await api.listProductionRuns({
          search: search || undefined,
          status: statusFilter === "" ? undefined : statusFilter,
          page,
          page_size: pageSize,
        });
        setRuns(res.items);
        setTotal(res.total);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load production runs.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [search, statusFilter, page]);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Production Runs</h2>
          <p className="text-xs text-slate-500">
            Track manufacturing batches from Draft → Planned → In Progress → Completed → Posted.
          </p>
        </div>
        {canManage && (
          <Link
            to="/production/runs/new"
            className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3.5 py-2 text-xs font-semibold text-white hover:bg-slate-800"
          >
            <Plus className="h-3.5 w-3.5" /> Create Production Run
          </Link>
        )}
      </div>

      <StatusNotice error={error} />

      <div className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-2">
        <input
          type="text"
          placeholder="Search order number, batch, or product..."
          value={search}
          onChange={(e) => {
            setPage(1);
            setSearch(e.target.value);
          }}
          className="rounded-lg border border-slate-300 px-3 py-2 text-xs"
        />
        <select
          aria-label="Filter production status"
          value={statusFilter}
          onChange={(e) => {
            setPage(1);
            setStatusFilter(e.target.value as "" | ProductionStatus);
          }}
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs"
        >
          <option value="">All Statuses</option>
          <option value="DRAFT">Draft</option>
          <option value="PLANNED">Planned</option>
          <option value="IN_PROGRESS">In Progress</option>
          <option value="COMPLETED">Completed</option>
          <option value="POSTED">Posted</option>
          <option value="CANCELLED">Cancelled</option>
        </select>
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        {loading ? (
          <div className="p-8 text-center text-xs text-slate-500">Loading production runs...</div>
        ) : runs.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500">No production runs found.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Order / Batch</th>
                  <th className="px-4 py-3 font-medium">Product (BOM)</th>
                  <th className="px-4 py-3 font-medium">Date</th>
                  <th className="px-4 py-3 font-medium">Expected</th>
                  <th className="px-4 py-3 font-medium">Actual Good</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {runs.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-50/70">
                    <td className="px-4 py-3">
                      <div className="font-mono font-medium text-slate-900">{r.order_number}</div>
                      <div className="font-mono text-[11px] text-slate-500">{r.batch_number}</div>
                    </td>
                    <td className="px-4 py-3 text-slate-700">
                      {r.product_name} (v{r.bom_version_snapshot})
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-600">{r.production_date}</td>
                    <td className="px-4 py-3 font-mono">{Number(r.expected_output)}</td>
                    <td className="px-4 py-3 font-mono font-medium text-slate-900">
                      {Number(r.actual_good_output)}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium ${
                          STATUS_BADGE[r.status]
                        }`}
                      >
                        {r.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <Link
                        to={`/production/runs/${r.id}`}
                        className="inline-flex items-center gap-1 rounded border border-slate-200 px-2.5 py-1 text-[11px] font-medium text-slate-700 hover:bg-slate-50"
                      >
                        <Eye className="h-3 w-3" /> Open
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
