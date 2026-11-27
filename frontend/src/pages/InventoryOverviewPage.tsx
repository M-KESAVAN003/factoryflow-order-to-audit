import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  Boxes,
  CheckCircle2,
  ClipboardCheck,
  Package,
  RefreshCw,
  ScrollText,
  ShoppingBag,
} from "lucide-react";
import { api, ApiError } from "../lib/api";
import { InventorySummary, ReconciliationReport } from "../types/inventoryPurchase";
import { StatusNotice } from "../components/MasterDataControls";

const CATEGORY_ROUTES: Record<string, string> = {
  RAW_MATERIAL: "/inventory/raw-materials",
  PACKAGING: "/inventory/packaging",
  FINISHED_GOOD: "/inventory/finished-goods",
};

const CATEGORY_ICONS = {
  RAW_MATERIAL: Boxes,
  PACKAGING: Package,
  FINISHED_GOOD: ShoppingBag,
};

export function InventoryOverviewPage() {
  const [summary, setSummary] = useState<InventorySummary | null>(null);
  const [reconciliation, setReconciliation] = useState<ReconciliationReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadOverview = async () => {
    setLoading(true);
    setError(null);
    try {
      const [sum, rec] = await Promise.all([
        api.inventorySummary(),
        api.reconcileInventory(),
      ]);
      setSummary(sum);
      setReconciliation(rec);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load inventory dashboard.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadOverview();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Inventory Overview</h2>
          <p className="text-xs text-slate-500">
            Live weighted-average valuation, category balances, and append-only ledger reconciliation.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => void loadOverview()}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            <RefreshCw className="h-3.5 w-3.5" /> Reconcile & Refresh
          </button>
          <Link
            to="/inventory/ledger"
            className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3.5 py-2 text-xs font-semibold text-white hover:bg-slate-800"
          >
            <ScrollText className="h-3.5 w-3.5" /> Stock Ledger
          </Link>
        </div>
      </div>

      <StatusNotice error={error} />

      {loading || !summary ? (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
          Loading inventory valuation...
        </div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
                Total Valuation
              </p>
              <p className="mt-2 text-2xl font-semibold text-slate-900 tabular-nums">
                ₹{Number(summary.total_stock_value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </p>
              <p className="mt-1 text-xs text-slate-500">
                Weighted-average across {summary.total_items} items
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
                Below Reorder (Red)
              </p>
              <p className="mt-2 text-2xl font-semibold text-rose-700 tabular-nums">
                {summary.low_stock_red_count}
              </p>
              <Link to="/inventory/alerts" className="mt-1 inline-block text-xs font-medium text-rose-700">
                Inspect low-stock alerts →
              </Link>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
                Approaching Reorder
              </p>
              <p className="mt-2 text-2xl font-semibold text-amber-700 tabular-nums">
                {summary.approaching_orange_count}
              </p>
              <p className="mt-1 text-xs text-slate-500">Within 20% of reorder threshold</p>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
                Ledger Reconciliation
              </p>
              <div className="mt-2 flex items-center gap-2">
                {reconciliation?.all_reconciled ? (
                  <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                ) : (
                  <AlertTriangle className="h-5 w-5 text-rose-600" />
                )}
                <span className="text-base font-semibold text-slate-900">
                  {reconciliation?.all_reconciled ? "100% Reconciled" : "Mismatch Detected"}
                </span>
              </div>
              <p className="mt-1 text-xs text-slate-500">
                {reconciliation?.checked_items ?? 0} balances verified vs ledger
              </p>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            {summary.categories.map((cat) => {
              const Icon = CATEGORY_ICONS[cat.item_type];
              return (
                <Link
                  key={cat.item_type}
                  to={CATEGORY_ROUTES[cat.item_type]}
                  className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition-colors hover:border-slate-300"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold text-slate-900">{cat.label}</span>
                    <Icon className="h-4 w-4 text-slate-500" />
                  </div>
                  <p className="mt-3 text-xl font-semibold text-slate-900 tabular-nums">
                    ₹{Number(cat.total_value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </p>
                  <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
                    <span>{cat.item_count} SKUs</span>
                    <span>{cat.low_stock_count} alert(s)</span>
                  </div>
                </Link>
              );
            })}
          </div>

          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
              <div className="flex items-center gap-2">
                <ClipboardCheck className="h-4 w-4 text-slate-500" />
                <h3 className="text-sm font-semibold text-slate-900">
                  Recent Stock Ledger Movements
                </h3>
              </div>
              <Link to="/inventory/ledger" className="text-xs font-medium text-sky-700">
                View all →
              </Link>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
                  <tr>
                    <th className="px-4 py-3 font-medium">Item</th>
                    <th className="px-4 py-3 font-medium">Movement</th>
                    <th className="px-4 py-3 font-medium">In / Out</th>
                    <th className="px-4 py-3 font-medium">Unit Cost</th>
                    <th className="px-4 py-3 font-medium">Reference</th>
                    <th className="px-4 py-3 font-medium">Balance After</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {summary.recent_movements.map((m) => (
                    <tr key={m.id} className="hover:bg-slate-50/70">
                      <td className="px-4 py-3">
                        <Link
                          to={`/inventory/items/${m.stock_item_id}`}
                          className="font-medium text-sky-700 hover:underline"
                        >
                          {m.stock_item_name}
                        </Link>
                        <div className="font-mono text-[11px] text-slate-400">
                          {m.stock_item_sku}
                        </div>
                      </td>
                      <td className="px-4 py-3 font-mono text-slate-700">{m.movement_type}</td>
                      <td className="px-4 py-3 font-mono">
                        {Number(m.quantity_in) > 0 ? (
                          <span className="text-emerald-700">
                            +{Number(m.quantity_in)} {m.base_unit_symbol}
                          </span>
                        ) : (
                          <span className="text-rose-700">
                            -{Number(m.quantity_out)} {m.base_unit_symbol}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 font-mono text-slate-700">
                        ₹{Number(m.unit_cost).toFixed(3)}
                      </td>
                      <td className="px-4 py-3 font-mono text-slate-600">
                        {m.reference_doc_type}: {m.reference_doc_id}
                      </td>
                      <td className="px-4 py-3 font-mono text-slate-900">
                        {Number(m.balance_qty_after)} {m.base_unit_symbol} (₹
                        {Number(m.balance_value_after).toLocaleString()})
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
