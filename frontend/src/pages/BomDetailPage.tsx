import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, CheckCircle2, Edit2, GitBranch, PowerOff } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api, ApiError } from "../lib/api";
import { hasPermission } from "../lib/permissions";
import { Bom } from "../types/bomProduction";
import { StatusNotice } from "../components/MasterDataControls";

export function BomDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const canManage = hasPermission(user, "bom:manage");

  const [bom, setBom] = useState<Bom | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const loadBom = async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      setBom(await api.getBom(id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load BOM.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadBom();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const handleToggleStatus = async (nextStatus: "ACTIVE" | "INACTIVE") => {
    if (!bom) return;
    setError(null);
    setSuccess(null);
    try {
      const updated = await api.updateBom(bom.id, { status: nextStatus });
      setBom(updated);
      setSuccess(`BOM v${updated.version_number} is now ${updated.status}.`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update BOM status.");
    }
  };

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
        Loading BOM details...
      </div>
    );
  }
  if (!bom) return <StatusNotice error={error ?? "BOM not found."} />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link
            to="/boms"
            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Back
          </Link>
          <div>
            <h2 className="text-lg font-semibold text-slate-900">
              {bom.product_name} — BOM v{bom.version_number}
            </h2>
            <p className="text-xs text-slate-500">
              {bom.product_sku} &bull; Effective {bom.effective_date} &bull; Status: {bom.status}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <Link
            to={`/boms/${bom.id}/versions`}
            className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            <GitBranch className="h-3.5 w-3.5" /> Version History
          </Link>
          {canManage && bom.status === "DRAFT" && (
            <Link
              to={`/boms/${bom.id}/edit`}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
            >
              <Edit2 className="h-3.5 w-3.5" /> Edit Draft
            </Link>
          )}
          {canManage && bom.status !== "ACTIVE" && (
            <button
              type="button"
              onClick={() => void handleToggleStatus("ACTIVE")}
              className="inline-flex items-center gap-1 rounded-lg bg-emerald-700 px-3.5 py-2 text-xs font-semibold text-white hover:bg-emerald-800"
            >
              <CheckCircle2 className="h-3.5 w-3.5" /> Activate Version
            </button>
          )}
          {canManage && bom.status === "ACTIVE" && (
            <button
              type="button"
              onClick={() => void handleToggleStatus("INACTIVE")}
              className="inline-flex items-center gap-1 rounded-lg border border-rose-200 bg-white px-3 py-2 text-xs font-semibold text-rose-700 hover:bg-rose-50"
            >
              <PowerOff className="h-3.5 w-3.5" /> Deactivate
            </button>
          )}
        </div>
      </div>

      <StatusNotice error={error} success={success} />

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-slate-500">Batch Size</p>
          <p className="mt-1 font-mono text-lg font-semibold text-slate-900">
            {Number(bom.batch_size)} batch
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-slate-500">Expected Yield Output</p>
          <p className="mt-1 font-mono text-lg font-semibold text-slate-900">
            {Number(bom.expected_output)} {bom.output_unit_symbol}
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-xs text-slate-500">Created By</p>
          <p className="mt-1 text-sm font-medium text-slate-900">{bom.created_by_email}</p>
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 px-5 py-4">
          <h3 className="text-sm font-semibold text-slate-900">BOM Material Breakdown</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">Input Item</th>
                <th className="px-4 py-3 font-medium">Category</th>
                <th className="px-4 py-3 font-medium">Standard Qty / Batch</th>
                <th className="px-4 py-3 font-medium">Available Stock</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {bom.lines.map((line) => (
                <tr key={line.id}>
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-900">{line.stock_item_name}</div>
                    <div className="font-mono text-[11px] text-slate-500">{line.stock_item_sku}</div>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{line.input_category}</td>
                  <td className="px-4 py-3 font-mono font-medium text-slate-900">
                    {Number(line.standard_quantity)} {line.unit_symbol}
                  </td>
                  <td className="px-4 py-3 font-mono text-slate-700">
                    {Number(line.available_stock)} {line.base_unit_symbol}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
