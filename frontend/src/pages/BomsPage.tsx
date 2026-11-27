import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Eye, GitBranch, Plus } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api, ApiError } from "../lib/api";
import { hasPermission } from "../lib/permissions";
import { Bom } from "../types/bomProduction";
import { PaginationFooter, StatusNotice } from "../components/MasterDataControls";

export function BomsPage() {
  const { user } = useAuth();
  const canManage = hasPermission(user, "bom:manage");

  const [boms, setBoms] = useState<Bom[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 15;
  const [activeFilter, setActiveFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await api.listBoms({
          is_active: activeFilter === "" ? undefined : activeFilter === "true",
          page,
          page_size: pageSize,
        });
        setBoms(res.items);
        setTotal(res.total);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load BOMs.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [activeFilter, page]);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Bills of Materials (BOM)</h2>
          <p className="text-xs text-slate-500">
            Versioned formulations defining standard raw material and packaging inputs per finished product.
          </p>
        </div>
        {canManage && (
          <Link
            to="/boms/new"
            className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3.5 py-2 text-xs font-semibold text-white hover:bg-slate-800"
          >
            <Plus className="h-3.5 w-3.5" /> Create BOM
          </Link>
        )}
      </div>

      <StatusNotice error={error} />

      <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <select
          aria-label="Filter active BOMs"
          value={activeFilter}
          onChange={(e) => {
            setPage(1);
            setActiveFilter(e.target.value);
          }}
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs"
        >
          <option value="">All Versions</option>
          <option value="true">Active Only</option>
          <option value="false">Draft / Historical</option>
        </select>
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        {loading ? (
          <div className="p-8 text-center text-xs text-slate-500">Loading BOMs...</div>
        ) : boms.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500">No BOMs configured.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Product</th>
                  <th className="px-4 py-3 font-medium">Version</th>
                  <th className="px-4 py-3 font-medium">Expected Output</th>
                  <th className="px-4 py-3 font-medium">Inputs</th>
                  <th className="px-4 py-3 font-medium">Effective Date</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {boms.map((b) => (
                  <tr key={b.id} className="hover:bg-slate-50/70">
                    <td className="px-4 py-3">
                      <div className="font-medium text-slate-900">{b.product_name}</div>
                      <div className="font-mono text-[11px] text-slate-500">{b.product_sku}</div>
                    </td>
                    <td className="px-4 py-3 font-mono font-semibold text-slate-800">
                      v{b.version_number}
                    </td>
                    <td className="px-4 py-3 font-mono">
                      {Number(b.expected_output)} {b.output_unit_symbol} / batch
                    </td>
                    <td className="px-4 py-3 text-slate-600">{b.lines.length} materials</td>
                    <td className="px-4 py-3 font-mono text-slate-600">{b.effective_date}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium ${
                          b.is_active
                            ? "bg-emerald-50 text-emerald-700"
                            : b.status === "DRAFT"
                            ? "bg-amber-50 text-amber-800"
                            : "bg-slate-100 text-slate-500"
                        }`}
                      >
                        {b.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <Link
                          to={`/boms/${b.id}`}
                          className="inline-flex items-center gap-1 rounded border border-slate-200 px-2.5 py-1 text-[11px] font-medium text-slate-700 hover:bg-slate-50"
                        >
                          <Eye className="h-3 w-3" /> Details
                        </Link>
                        <Link
                          to={`/boms/${b.id}/versions`}
                          className="inline-flex items-center gap-1 rounded border border-slate-200 px-2.5 py-1 text-[11px] font-medium text-slate-700 hover:bg-slate-50"
                        >
                          <GitBranch className="h-3 w-3" /> History
                        </Link>
                      </div>
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
