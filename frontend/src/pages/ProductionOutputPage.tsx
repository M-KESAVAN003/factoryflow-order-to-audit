import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { AlertTriangle, ArrowLeft } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { ProductionRun } from "../types/bomProduction";
import { StatusNotice } from "../components/MasterDataControls";

export function ProductionOutputPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [run, setRun] = useState<ProductionRun | null>(null);
  const [goodQty, setGoodQty] = useState("0");
  const [damagedPackets, setDamagedPackets] = useState("0");
  const [cartonsUsed, setCartonsUsed] = useState("0");
  const [packetsPerCarton, setPacketsPerCarton] = useState(20);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    const load = async () => {
      setLoading(true);
      try {
        const [r, prod] = await Promise.all([
          api.getProductionRun(id),
          api.getProductionRun(id).then((runObj) => api.getProduct(runObj.product_id)),
        ]);
        setRun(r);
        setPacketsPerCarton(prod.packets_per_carton || 20);
        setGoodQty(
          Number(r.actual_good_output) > 0
            ? String(Number(r.actual_good_output))
            : String(Number(r.expected_output))
        );
        setDamagedPackets(String(Number(r.damaged_packets)));
        const cartonMat = r.materials.find((m) =>
          m.stock_item_name.toLowerCase().includes("carton")
        );
        setCartonsUsed(
          cartonMat && Number(cartonMat.actual_quantity) > 0
            ? String(Number(cartonMat.actual_quantity))
            : String(Number(cartonMat?.planned_quantity ?? 0))
        );
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load output entry.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [id]);

  const capacity = Number(cartonsUsed || 0) * packetsPerCarton;
  const unpacked = Math.max(0, Number(goodQty || 0) - capacity);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id) return;
    setSubmitting(true);
    setError(null);
    try {
      await api.recordProductionOutput(id, {
        good_quantity: goodQty,
        damaged_packets: damagedPackets,
        cartons_used: cartonsUsed,
      });
      navigate(`/production/runs/${id}`, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save output.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
        Loading output form...
      </div>
    );
  }
  if (!run) return <StatusNotice error={error ?? "Run not found."} />;

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <div className="flex items-center gap-3">
        <Link
          to={`/production/runs/${run.id}`}
          className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Back
        </Link>
        <div>
          <h2 className="text-lg font-semibold text-slate-900">
            Actual Production Output — {run.order_number}
          </h2>
          <p className="text-xs text-slate-500">
            Only good packets are added to finished-goods inventory on posting.
          </p>
        </div>
      </div>

      <StatusNotice error={error} />

      <form
        onSubmit={handleSubmit}
        className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Expected Output</label>
            <input
              type="text"
              disabled
              value={`${Number(run.expected_output)} packets`}
              className="w-full rounded-lg border border-slate-200 bg-slate-100 px-3 py-2 font-mono text-xs"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">
              Actual Good Packets
            </label>
            <input
              type="number"
              step="0.000001"
              min="0"
              required
              value={goodQty}
              onChange={(e) => setGoodQty(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">
              Damaged Packets
            </label>
            <input
              type="number"
              step="0.000001"
              min="0"
              required
              value={damagedPackets}
              onChange={(e) => setDamagedPackets(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">
              Cartons Used ({packetsPerCarton} pkts/carton)
            </label>
            <input
              type="number"
              step="0.000001"
              min="0"
              required
              value={cartonsUsed}
              onChange={(e) => setCartonsUsed(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs"
            />
          </div>
        </div>

        {unpacked > 0 && (
          <div className="flex items-start gap-2 rounded-lg border border-amber-300 bg-amber-50 p-3 text-xs text-amber-900">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />
            <span>
              {cartonsUsed} cartons hold {capacity} packets. {goodQty} packets were produced.
              Therefore, {unpacked} packets remain unpacked.
            </span>
          </div>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <Link
            to={`/production/runs/${run.id}`}
            className="rounded-lg border border-slate-300 px-4 py-2 text-xs font-medium text-slate-700"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={submitting}
            className="rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
          >
            {submitting ? "Saving..." : "Record Output"}
          </button>
        </div>
      </form>
    </div>
  );
}
