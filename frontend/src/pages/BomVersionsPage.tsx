import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { Bom } from "../types/bomProduction";
import { StatusNotice } from "../components/MasterDataControls";

export function BomVersionsPage() {
  const { id } = useParams<{ id: string }>();
  const [versions, setVersions] = useState<Bom[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    const load = async () => {
      setLoading(true);
      try {
        setVersions(await api.getBomVersions(id));
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load BOM history.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [id]);

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <Link
          to={id ? `/boms/${id}` : "/boms"}
          className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Back
        </Link>
        <div>
          <h2 className="text-lg font-semibold text-slate-900">BOM Version History</h2>
          <p className="text-xs text-slate-500">
            Historical BOM versions remain preserved for all past production runs.
          </p>
        </div>
      </div>

      <StatusNotice error={error} />

      {loading ? (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
          Loading BOM versions...
        </div>
      ) : (
        <div className="space-y-3">
          {versions.map((v) => (
            <div
              key={v.id}
              className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <span className="font-mono text-sm font-semibold text-slate-900">
                    v{v.version_number}
                  </span>
                  <span className="ml-2 text-xs text-slate-600">
                    Expected: {Number(v.expected_output)} {v.output_unit_symbol} &bull; Effective{" "}
                    {v.effective_date}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium ${
                      v.is_active
                        ? "bg-emerald-50 text-emerald-700"
                        : "bg-slate-100 text-slate-600"
                    }`}
                  >
                    {v.status}
                  </span>
                  <Link
                    to={`/boms/${v.id}`}
                    className="text-xs font-medium text-sky-700 hover:underline"
                  >
                    Inspect →
                  </Link>
                </div>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {v.lines.map((l) => (
                  <span
                    key={l.id}
                    className="rounded border border-slate-200 bg-slate-50 px-2.5 py-1 font-mono text-[11px] text-slate-700"
                  >
                    {l.stock_item_name}: {Number(l.standard_quantity)} {l.unit_symbol}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
