import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CheckCircle2, PlusCircle, RotateCcw } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api, ApiError } from "../lib/api";
import { hasPermission } from "../lib/permissions";
import { ProductionExpense } from "../types/costingPayment";
import { ProductionRun } from "../types/bomProduction";
import { StatusNotice } from "../components/MasterDataControls";

export function ProductionExpensesPage() {
  const { user } = useAuth();
  const canManage = hasPermission(user, "expenses:manage");
  const [runs, setRuns] = useState<ProductionRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState("");
  const [expenses, setExpenses] = useState<ProductionExpense[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const loadExpenses = async (runId: string) => {
    if (!runId) return;
    try {
      setExpenses(await api.listRunExpenses(runId));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load expenses.");
    }
  };

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const res = await api.listProductionRuns({ page_size: 50 });
        setRuns(res.items);
        if (res.items[0]) {
          setSelectedRunId(res.items[0].id);
          await loadExpenses(res.items[0].id);
        }
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load production runs.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

  const handleAction = async (fn: () => Promise<ProductionExpense>, msg: string) => {
    setError(null);
    setSuccess(null);
    try {
      await fn();
      setSuccess(msg);
      await loadExpenses(selectedRunId);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Action failed.");
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Production Expense Management</h2>
          <p className="text-xs text-slate-500">
            Track Labour, Gas, Electricity, Power, Maintenance, and Overhead expenses per production run.
          </p>
        </div>
        {canManage && selectedRunId && (
          <Link
            to={`/costing/runs/${selectedRunId}/expenses/new`}
            className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3 py-2 text-xs font-medium text-white"
          >
            <PlusCircle className="h-4 w-4" /> Add Production Expense
          </Link>
        )}
      </div>

      <StatusNotice error={error} success={success} />

      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <label className="mb-1 block text-xs font-medium text-slate-700">Select Production Run</label>
        <select
          value={selectedRunId}
          onChange={(e) => {
            setSelectedRunId(e.target.value);
            void loadExpenses(e.target.value);
          }}
          className="w-full max-w-md rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs"
        >
          {runs.map((r) => (
            <option key={r.id} value={r.id}>
              {r.order_number} — {r.product_name} ({r.status})
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
          Loading expenses...
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">Expense #</th>
                <th className="px-4 py-3 font-medium">Category</th>
                <th className="px-4 py-3 font-medium">Description</th>
                <th className="px-4 py-3 font-medium">Date</th>
                <th className="px-4 py-3 font-medium">Amount</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {expenses.map((ex) => (
                <tr key={ex.id}>
                  <td className="px-4 py-3 font-mono font-semibold text-slate-900">{ex.expense_number}</td>
                  <td className="px-4 py-3">{ex.category}</td>
                  <td className="px-4 py-3">{ex.description}</td>
                  <td className="px-4 py-3">{ex.expense_date}</td>
                  <td className="px-4 py-3 font-mono font-semibold">Rs {Number(ex.amount).toFixed(2)}</td>
                  <td className="px-4 py-3">
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium">
                      {ex.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 space-x-2">
                    {canManage && ex.status === "DRAFT" && (
                      <button
                        type="button"
                        onClick={() =>
                          handleAction(() => api.postRunExpense(selectedRunId, ex.id), "Expense posted.")
                        }
                        className="inline-flex items-center gap-1 text-emerald-700 hover:underline"
                      >
                        <CheckCircle2 className="h-3.5 w-3.5" /> Post
                      </button>
                    )}
                    {canManage &&
                      ex.status === "POSTED" &&
                      !ex.reversal_of_id &&
                      !expenses.some((r) => r.reversal_of_id === ex.id) && (
                      <button
                        type="button"
                        onClick={() =>
                          handleAction(
                            () => api.reverseRunExpense(selectedRunId, ex.id),
                            "Traceable expense reversal posted."
                          )
                        }
                        className="inline-flex items-center gap-1 text-rose-700 hover:underline"
                      >
                        <RotateCcw className="h-3.5 w-3.5" /> Reverse
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {expenses.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-slate-400">
                    No expenses logged for this run.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
