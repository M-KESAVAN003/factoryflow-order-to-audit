import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { ProductionRun } from "../types/bomProduction";
import { StatusNotice } from "../components/MasterDataControls";

interface MaterialInputRow {
  stock_item_id: string;
  name: string;
  unit_symbol: string;
  planned: string;
  available: string;
  actual_quantity: string;
  damaged_quantity: string;
}

export function ProductionMaterialIssuePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [run, setRun] = useState<ProductionRun | null>(null);
  const [rows, setRows] = useState<MaterialInputRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    const load = async () => {
      setLoading(true);
      try {
        const r = await api.getProductionRun(id);
        setRun(r);
        setRows(
          r.materials.map((m) => ({
            stock_item_id: m.stock_item_id,
            name: m.stock_item_name,
            unit_symbol: m.unit_symbol,
            planned: String(Number(m.planned_quantity)),
            available: String(Number(m.available_stock)),
            actual_quantity:
              Number(m.actual_quantity) > 0
                ? String(Number(m.actual_quantity))
                : String(Number(m.planned_quantity)),
            damaged_quantity: String(Number(m.damaged_quantity)),
          }))
        );
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load materials.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [id]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id) return;
    setSubmitting(true);
    setError(null);
    try {
      await api.recordProductionConsumption(
        id,
        rows.map((r) => ({
          stock_item_id: r.stock_item_id,
          actual_quantity: r.actual_quantity,
          damaged_quantity: r.damaged_quantity,
        }))
      );
      navigate(`/production/runs/${id}`, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to record material issue.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
        Loading material issue screen...
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
        <div>
          <h2 className="text-lg font-semibold text-slate-900">
            Material Issue — {run.order_number}
          </h2>
          <p className="text-xs text-slate-500">
            Confirm actual raw materials and packaging consumed (including damaged pouches).
          </p>
        </div>
      </div>

      <StatusNotice error={error} />

      <form
        onSubmit={handleSubmit}
        className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm"
      >
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">Material</th>
                <th className="px-4 py-3 font-medium">Available</th>
                <th className="px-4 py-3 font-medium">Planned</th>
                <th className="px-4 py-3 font-medium">Actual Consumed</th>
                <th className="px-4 py-3 font-medium">Damaged / Scrap</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.map((r, idx) => (
                <tr key={r.stock_item_id}>
                  <td className="px-4 py-3 font-medium text-slate-900">
                    {r.name} ({r.unit_symbol})
                  </td>
                  <td className="px-4 py-3 font-mono text-slate-600">{r.available}</td>
                  <td className="px-4 py-3 font-mono text-slate-700">{r.planned}</td>
                  <td className="px-4 py-3">
                    <input
                      type="number"
                      step="0.000001"
                      min="0"
                      required
                      value={r.actual_quantity}
                      onChange={(e) =>
                        setRows((prev) =>
                          prev.map((row, i) =>
                            i === idx ? { ...row, actual_quantity: e.target.value } : row
                          )
                        )
                      }
                      className="w-28 rounded border border-slate-300 px-2.5 py-1.5 font-mono text-xs"
                    />
                  </td>
                  <td className="px-4 py-3">
                    <input
                      type="number"
                      step="0.000001"
                      min="0"
                      required
                      value={r.damaged_quantity}
                      onChange={(e) =>
                        setRows((prev) =>
                          prev.map((row, i) =>
                            i === idx ? { ...row, damaged_quantity: e.target.value } : row
                          )
                        )
                      }
                      className="w-24 rounded border border-slate-300 px-2.5 py-1.5 font-mono text-xs"
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex justify-end gap-2 border-t border-slate-200 bg-slate-50 px-5 py-3">
          <Link
            to={`/production/runs/${run.id}`}
            className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-xs font-medium text-slate-700"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={submitting}
            className="rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
          >
            {submitting ? "Saving..." : "Save Material Consumption"}
          </button>
        </div>
      </form>
    </div>
  );
}
