import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Plus } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { ProductionRun } from "../types/bomProduction";
import { StatusNotice } from "../components/MasterDataControls";

export function ProductionWastagePage() {
  const { id } = useParams<{ id: string }>();
  const [run, setRun] = useState<ProductionRun | null>(null);
  const [stockItemId, setStockItemId] = useState("");
  const [wastageType, setWastageType] = useState("DAMAGED_POUCH");
  const [quantity, setQuantity] = useState("1");
  const [reason, setReason] = useState("");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const loadRun = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const r = await api.getProductionRun(id);
      setRun(r);
      if (r.materials[0] && !stockItemId) {
        setStockItemId(r.materials[0].stock_item_id);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load wastage view.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadRun();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id || !run) return;
    setError(null);
    setSuccess(null);
    try {
      const mat = run.materials.find((m) => m.stock_item_id === stockItemId);
      const updated = await api.recordProductionWastage(id, {
        stock_item_id: stockItemId || null,
        wastage_type: wastageType,
        quantity,
        unit_id: mat?.unit_id ?? null,
        reason: reason.trim(),
        notes: notes.trim() || null,
      });
      setRun(updated);
      setReason("");
      setNotes("");
      setSuccess("Wastage / scrap record logged.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to log wastage.");
    }
  };

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
        Loading wastage tracker...
      </div>
    );
  }
  if (!run) return <StatusNotice error={error ?? "Run not found."} />;

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <div className="flex items-center gap-3">
        <Link
          to={`/production/runs/${run.id}`}
          className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Back
        </Link>
        <h2 className="text-lg font-semibold text-slate-900">
          Wastage & Scrap Log — {run.order_number}
        </h2>
      </div>

      <StatusNotice error={error} success={success} />

      <form
        onSubmit={handleSubmit}
        className="grid gap-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:grid-cols-5"
      >
        <select
          value={wastageType}
          onChange={(e) => setWastageType(e.target.value)}
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs"
        >
          <option value="DAMAGED_POUCH">Damaged Pouch</option>
          <option value="DAMAGED_PACKET">Damaged Packet</option>
          <option value="SCRAP">Process Scrap</option>
          <option value="PROCESS_LOSS">Process Loss</option>
        </select>
        <select
          value={stockItemId}
          onChange={(e) => setStockItemId(e.target.value)}
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs"
        >
          <option value="">General / Finished</option>
          {run.materials.map((m) => (
            <option key={m.stock_item_id} value={m.stock_item_id}>
              {m.stock_item_name}
            </option>
          ))}
        </select>
        <input
          type="number"
          step="0.000001"
          min="0.000001"
          required
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
          className="rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs"
        />
        <input
          type="text"
          required
          minLength={2}
          placeholder="Wastage reason..."
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          className="rounded-lg border border-slate-300 px-3 py-2 text-xs"
        />
        <button
          type="submit"
          className="inline-flex items-center justify-center gap-1 rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800"
        >
          <Plus className="h-3.5 w-3.5" /> Record Wastage
        </button>
      </form>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        {run.wastages.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500">
            No wastage entries recorded for this run.
          </div>
        ) : (
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">Type</th>
                <th className="px-4 py-3 font-medium">Material</th>
                <th className="px-4 py-3 font-medium">Quantity</th>
                <th className="px-4 py-3 font-medium">Reason</th>
                <th className="px-4 py-3 font-medium">Recorded By</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {run.wastages.map((w) => (
                <tr key={w.id}>
                  <td className="px-4 py-3 font-mono text-slate-800">{w.wastage_type}</td>
                  <td className="px-4 py-3 text-slate-700">{w.stock_item_name ?? "General"}</td>
                  <td className="px-4 py-3 font-mono">
                    {Number(w.quantity)} {w.unit_symbol ?? ""}
                  </td>
                  <td className="px-4 py-3 text-slate-600">{w.reason}</td>
                  <td className="px-4 py-3 text-slate-500">{w.recorded_by_email}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
