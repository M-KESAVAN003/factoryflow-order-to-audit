import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AlertTriangle, ArrowLeft } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { Bom } from "../types/bomProduction";
import { Product } from "../types/masterData";
import { StatusNotice } from "../components/MasterDataControls";

export function ProductionRunFormPage() {
  const navigate = useNavigate();
  const [products, setProducts] = useState<Product[]>([]);
  const [boms, setBoms] = useState<Bom[]>([]);

  const [orderNumber, setOrderNumber] = useState(`PRD-${Date.now().toString().slice(-6)}`);
  const [productId, setProductId] = useState("");
  const [bomId, setBomId] = useState("");
  const [batchNumber, setBatchNumber] = useState(`BATCH-${Date.now().toString().slice(-4)}`);
  const [productionDate, setProductionDate] = useState(new Date().toISOString().slice(0, 10));
  const [plannedBatches, setPlannedBatches] = useState("1");
  const [tolerance, setTolerance] = useState("3.00");
  const [notes, setNotes] = useState("");

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const [prodRes, bomRes] = await Promise.all([
          api.listProducts({ is_active: true, page_size: 100 }),
          api.listBoms({ page_size: 100 }),
        ]);
        setProducts(prodRes.items);
        setBoms(bomRes.items);
        if (prodRes.items[0]) {
          setProductId(prodRes.items[0].id);
          const activeBom = bomRes.items.find(
            (b) => b.product_id === prodRes.items[0].id && b.is_active
          );
          if (activeBom) setBomId(activeBom.id);
        }
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load production form.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

  const productBoms = boms.filter((b) => b.product_id === productId);
  const selectedBom = boms.find((b) => b.id === bomId) ?? productBoms.find((b) => b.is_active);
  const batchRatio =
    selectedBom && Number(selectedBom.batch_size) > 0
      ? Number(plannedBatches || 0) / Number(selectedBom.batch_size)
      : 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const created = await api.createProductionRun({
        order_number: orderNumber.trim().toUpperCase(),
        product_id: productId,
        bom_id: selectedBom?.id || null,
        batch_number: batchNumber.trim().toUpperCase(),
        production_date: productionDate,
        planned_batches: plannedBatches,
        variance_tolerance_pct: tolerance,
        notes: notes.trim() || null,
      });
      navigate(`/production/runs/${created.id}`, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create production run.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
        Loading production planner...
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <div className="flex items-center gap-3">
        <Link
          to="/production/runs"
          className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Back
        </Link>
        <h2 className="text-lg font-semibold text-slate-900">Create Production Run</h2>
      </div>

      <StatusNotice error={error} />

      <form
        onSubmit={handleSubmit}
        className="space-y-5 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
      >
        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Order Number</label>
            <input
              type="text"
              required
              value={orderNumber}
              onChange={(e) => setOrderNumber(e.target.value.toUpperCase())}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Product</label>
            <select
              required
              value={productId}
              onChange={(e) => {
                setProductId(e.target.value);
                const nextActive = boms.find(
                  (b) => b.product_id === e.target.value && b.is_active
                );
                setBomId(nextActive?.id ?? "");
              }}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs"
            >
              {products.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.sku})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">BOM Version</label>
            <select
              value={bomId}
              onChange={(e) => setBomId(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs"
            >
              {productBoms.map((b) => (
                <option key={b.id} value={b.id}>
                  v{b.version_number} ({b.status}) — {Number(b.expected_output)}{" "}
                  {b.output_unit_symbol}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Batch Number</label>
            <input
              type="text"
              required
              value={batchNumber}
              onChange={(e) => setBatchNumber(e.target.value.toUpperCase())}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Production Date</label>
            <input
              type="date"
              required
              value={productionDate}
              onChange={(e) => setProductionDate(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Planned Batches</label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              required
              value={plannedBatches}
              onChange={(e) => setPlannedBatches(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">
              Variance Tolerance (%)
            </label>
            <input
              type="number"
              step="0.1"
              min="0"
              required
              value={tolerance}
              onChange={(e) => setTolerance(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs"
            />
          </div>
          <div className="sm:col-span-2">
            <label className="mb-1 block text-xs font-medium text-slate-700">Notes</label>
            <input
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs"
            />
          </div>
        </div>

        {selectedBom && (
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <div className="mb-2 flex items-center justify-between text-xs font-semibold text-slate-900">
              <span>
                Planned Material Requirements (Expected Output:{" "}
                {(Number(selectedBom.expected_output) * batchRatio).toFixed(2)}{" "}
                {selectedBom.output_unit_symbol})
              </span>
            </div>
            <div className="space-y-1.5 text-xs">
              {selectedBom.lines.map((l) => {
                const req = Number(l.standard_quantity) * batchRatio;
                const avail = Number(l.available_stock);
                const low = avail < req;
                return (
                  <div
                    key={l.id}
                    className={`flex items-center justify-between rounded border px-3 py-2 ${
                      low
                        ? "border-rose-200 bg-rose-50 text-rose-800"
                        : "border-slate-200 bg-white text-slate-800"
                    }`}
                  >
                    <span>
                      {l.stock_item_name} ({l.input_category})
                    </span>
                    <span className="flex items-center gap-2 font-mono">
                      Required: {req.toFixed(2)} {l.unit_symbol} | Avail: {avail.toFixed(2)}{" "}
                      {l.base_unit_symbol}
                      {low && <AlertTriangle className="h-3.5 w-3.5 text-rose-600" />}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        <div className="flex justify-end gap-2">
          <Link
            to="/production/runs"
            className="rounded-lg border border-slate-300 px-4 py-2 text-xs font-medium text-slate-700"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={submitting || !selectedBom}
            className="rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
          >
            {submitting ? "Creating..." : "Create Draft Production Run"}
          </button>
        </div>
      </form>
    </div>
  );
}
