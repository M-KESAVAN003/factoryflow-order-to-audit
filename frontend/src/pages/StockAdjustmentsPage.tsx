import React, { useEffect, useState } from "react";
import { CheckCircle2, Plus } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api, ApiError } from "../lib/api";
import { hasPermission } from "../lib/permissions";
import { StockAdjustment } from "../types/inventoryPurchase";
import { StockItem } from "../types/masterData";
import { PaginationFooter, StatusNotice } from "../components/MasterDataControls";

export function StockAdjustmentsPage() {
  const { user } = useAuth();
  const canManage = hasPermission(user, "inventory:manage");

  const [adjustments, setAdjustments] = useState<StockAdjustment[]>([]);
  const [stockItems, setStockItems] = useState<StockItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 15;

  const [showForm, setShowForm] = useState(false);
  const [stockItemId, setStockItemId] = useState("");
  const [physicalCount, setPhysicalCount] = useState("0");
  const [reason, setReason] = useState("");
  const [notes, setNotes] = useState("");
  const [adjDate, setAdjDate] = useState(new Date().toISOString().slice(0, 10));

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [adjRes, itemsRes] = await Promise.all([
        api.listAdjustments({ page, page_size: pageSize }),
        api.listStockItems({ page_size: 100 }),
      ]);
      setAdjustments(adjRes.items);
      setTotal(adjRes.total);
      setStockItems(itemsRes.items);
      if (itemsRes.items.length > 0 && !stockItemId) {
        setStockItemId(itemsRes.items[0].id);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load stock adjustments.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    try {
      const created = await api.createAdjustment({
        stock_item_id: stockItemId,
        physical_count: physicalCount,
        reason: reason.trim(),
        supporting_notes: notes.trim() || null,
        adjustment_date: adjDate,
      });
      setSuccess(
        `Submitted adjustment for ${created.stock_item_name} (diff: ${Number(created.difference)} ${created.base_unit_symbol}). Approve to post ledger entry.`
      );
      setReason("");
      setNotes("");
      setShowForm(false);
      await loadData();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to submit adjustment.");
    }
  };

  const handleApprove = async (adj: StockAdjustment) => {
    setError(null);
    setSuccess(null);
    try {
      const approved = await api.approveAdjustment(adj.id);
      setSuccess(
        `Approved adjustment for ${approved.stock_item_name}; StockLedger updated.`
      );
      await loadData();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to approve adjustment.");
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Stock Adjustments</h2>
          <p className="text-xs text-slate-500">
            Controlled physical count reconciliations requiring reason and approval before updating ledger.
          </p>
        </div>
        {canManage && (
          <button
            type="button"
            onClick={() => setShowForm((prev) => !prev)}
            className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3.5 py-2 text-xs font-semibold text-white hover:bg-slate-800"
          >
            <Plus className="h-3.5 w-3.5" />
            {showForm ? "Close Form" : "New Adjustment"}
          </button>
        )}
      </div>

      <StatusNotice error={error} success={success} />

      {showForm && canManage && (
        <form
          onSubmit={handleCreate}
          className="grid gap-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:grid-cols-2 lg:grid-cols-3"
        >
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Stock Item</label>
            <select
              required
              value={stockItemId}
              onChange={(e) => setStockItemId(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs"
            >
              {stockItems.map((i) => (
                <option key={i.id} value={i.id}>
                  {i.name} ({i.sku}) — {i.base_unit_symbol}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Physical Count</label>
            <input
              type="number"
              step="0.000001"
              min="0"
              required
              value={physicalCount}
              onChange={(e) => setPhysicalCount(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Adjustment Date</label>
            <input
              type="date"
              required
              value={adjDate}
              onChange={(e) => setAdjDate(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Reason (Required)</label>
            <input
              type="text"
              required
              minLength={3}
              placeholder="e.g. Cycle count variance / spoilage"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Supporting Notes</label>
            <input
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs"
            />
          </div>
          <div className="flex items-end">
            <button
              type="submit"
              className="w-full rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800"
            >
              Submit for Approval
            </button>
          </div>
        </form>
      )}

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        {loading ? (
          <div className="p-8 text-center text-xs text-slate-500">Loading adjustments...</div>
        ) : adjustments.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500">
            No stock adjustments recorded yet.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Date</th>
                  <th className="px-4 py-3 font-medium">Item</th>
                  <th className="px-4 py-3 font-medium">Book Bal</th>
                  <th className="px-4 py-3 font-medium">Physical</th>
                  <th className="px-4 py-3 font-medium">Difference</th>
                  <th className="px-4 py-3 font-medium">Reason</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  {canManage && <th className="px-4 py-3 font-medium">Action</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {adjustments.map((a) => (
                  <tr key={a.id} className="hover:bg-slate-50/70">
                    <td className="px-4 py-3 font-mono text-slate-600">{a.adjustment_date}</td>
                    <td className="px-4 py-3">
                      <div className="font-medium text-slate-900">{a.stock_item_name}</div>
                      <div className="font-mono text-[11px] text-slate-500">{a.stock_item_sku}</div>
                    </td>
                    <td className="px-4 py-3 font-mono">
                      {Number(a.current_balance)} {a.base_unit_symbol}
                    </td>
                    <td className="px-4 py-3 font-mono">
                      {Number(a.physical_count)} {a.base_unit_symbol}
                    </td>
                    <td className="px-4 py-3 font-mono font-medium">
                      <span
                        className={
                          Number(a.difference) >= 0 ? "text-emerald-700" : "text-rose-700"
                        }
                      >
                        {Number(a.difference) > 0 ? `+${Number(a.difference)}` : Number(a.difference)}{" "}
                        {a.base_unit_symbol}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-700">{a.reason}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium ${
                          a.status === "APPROVED"
                            ? "bg-emerald-50 text-emerald-700"
                            : "bg-amber-50 text-amber-800"
                        }`}
                      >
                        {a.status}
                      </span>
                    </td>
                    {canManage && (
                      <td className="px-4 py-3">
                        {a.status === "PENDING" ? (
                          <button
                            type="button"
                            onClick={() => void handleApprove(a)}
                            className="inline-flex items-center gap-1 rounded bg-emerald-700 px-2.5 py-1 text-[11px] font-semibold text-white hover:bg-emerald-800"
                          >
                            <CheckCircle2 className="h-3 w-3" /> Approve & Post
                          </button>
                        ) : (
                          <span className="text-[11px] text-slate-400">
                            By {a.approved_by_email}
                          </span>
                        )}
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
    </div>
  );
}
