import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../lib/api";
import { MovementType, StockLedgerEntry } from "../types/inventoryPurchase";
import { PaginationFooter, StatusNotice } from "../components/MasterDataControls";

const MOVEMENT_TYPES: MovementType[] = [
  "OPENING_STOCK",
  "PURCHASE_RECEIPT",
  "PRODUCTION_ISSUE",
  "PRODUCTION_OUTPUT",
  "SALES_DISPATCH",
  "SALES_RETURN",
  "PURCHASE_RETURN",
  "STOCK_ADJUSTMENT",
  "REVERSAL",
];

export function StockLedgerPage() {
  const [entries, setEntries] = useState<StockLedgerEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 25;

  const [movementFilter, setMovementFilter] = useState<"" | MovementType>("");
  const [refFilter, setRefFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadLedger = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listStockLedger({
        movement_type: movementFilter === "" ? undefined : movementFilter,
        reference_doc_id: refFilter || undefined,
        page,
        page_size: pageSize,
      });
      setEntries(res.items);
      setTotal(res.total);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load stock ledger.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadLedger();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [movementFilter, refFilter, page]);

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">
          Append-Only Stock Ledger
        </h2>
        <p className="text-xs text-slate-500">
          Immutable chronological record of every inventory movement, source document, and valuation snapshot.
        </p>
      </div>

      <StatusNotice error={error} />

      <div className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-3">
        <input
          type="text"
          placeholder="Search reference document (e.g. BENCHMARK-FLOUR-001)..."
          value={refFilter}
          onChange={(e) => {
            setPage(1);
            setRefFilter(e.target.value);
          }}
          className="rounded-lg border border-slate-300 px-3 py-2 text-xs focus:border-slate-900 focus:outline-none"
        />
        <select
          aria-label="Filter movement type"
          value={movementFilter}
          onChange={(e) => {
            setPage(1);
            setMovementFilter(e.target.value as "" | MovementType);
          }}
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs focus:border-slate-900 focus:outline-none"
        >
          <option value="">All Movement Types</option>
          {MOVEMENT_TYPES.map((mt) => (
            <option key={mt} value={mt}>
              {mt}
            </option>
          ))}
        </select>
        <div className="flex items-center text-xs text-slate-500">
          Showing {entries.length} of {total} immutable entries
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        {loading ? (
          <div className="p-8 text-center text-xs text-slate-500">Loading stock ledger...</div>
        ) : entries.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500">No ledger movements found.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Date</th>
                  <th className="px-4 py-3 font-medium">Item</th>
                  <th className="px-4 py-3 font-medium">Type</th>
                  <th className="px-4 py-3 font-medium">Qty In</th>
                  <th className="px-4 py-3 font-medium">Qty Out</th>
                  <th className="px-4 py-3 font-medium">Unit Cost</th>
                  <th className="px-4 py-3 font-medium">Value</th>
                  <th className="px-4 py-3 font-medium">Reference</th>
                  <th className="px-4 py-3 font-medium">Balance After</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {entries.map((e) => (
                  <tr key={e.id} className="hover:bg-slate-50/70">
                    <td className="whitespace-nowrap px-4 py-3 font-mono text-[11px] text-slate-500">
                      {new Date(e.transaction_date).toLocaleString()}
                    </td>
                    <td className="px-4 py-3">
                      <Link
                        to={`/inventory/items/${e.stock_item_id}`}
                        className="font-medium text-sky-700 hover:underline"
                      >
                        {e.stock_item_name}
                      </Link>
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-700">{e.movement_type}</td>
                    <td className="px-4 py-3 font-mono text-emerald-700">
                      {Number(e.quantity_in) > 0
                        ? `+${Number(e.quantity_in)} ${e.base_unit_symbol}`
                        : "—"}
                    </td>
                    <td className="px-4 py-3 font-mono text-rose-700">
                      {Number(e.quantity_out) > 0
                        ? `-${Number(e.quantity_out)} ${e.base_unit_symbol}`
                        : "—"}
                    </td>
                    <td className="px-4 py-3 font-mono">₹{Number(e.unit_cost).toFixed(3)}</td>
                    <td className="px-4 py-3 font-mono">₹{Number(e.total_value).toLocaleString()}</td>
                    <td className="px-4 py-3 font-mono text-slate-600">
                      {e.reference_doc_type}: {e.reference_doc_id}
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-900">
                      {Number(e.balance_qty_after)} {e.base_unit_symbol} (₹
                      {Number(e.balance_value_after).toLocaleString()})
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
