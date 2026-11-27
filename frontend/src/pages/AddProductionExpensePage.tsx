import React, { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { ExpenseCategory } from "../types/costingPayment";
import { StatusNotice } from "../components/MasterDataControls";

export function AddProductionExpensePage() {
  const { runId } = useParams<{ runId: string }>();
  const navigate = useNavigate();

  const [category, setCategory] = useState<ExpenseCategory>("LABOUR");
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("1200.00");
  const [expenseDate, setExpenseDate] = useState(new Date().toISOString().slice(0, 10));
  const [autoPost, setAutoPost] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!runId) return;
    setSaving(true);
    setError(null);
    try {
      await api.addRunExpense(runId, {
        category,
        description,
        amount,
        expense_date: expenseDate,
        auto_post: autoPost,
      });
      navigate(`/costing/runs/${runId}`, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save expense.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-xl space-y-5">
      <div className="flex items-center gap-3">
        <Link
          to={runId ? `/costing/runs/${runId}` : "/costing/expenses"}
          className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Back
        </Link>
        <h2 className="text-lg font-semibold text-slate-900">Add Production Expense</h2>
      </div>

      <StatusNotice error={error} />

      <form
        onSubmit={handleSubmit}
        className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm text-xs"
      >
        <div>
          <label className="mb-1 block font-medium text-slate-700">Expense Category</label>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value as ExpenseCategory)}
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2"
          >
            <option value="LABOUR">Labour</option>
            <option value="GAS">Gas</option>
            <option value="ELECTRICITY">Electricity</option>
            <option value="POWER">Power</option>
            <option value="MAINTENANCE">Maintenance</option>
            <option value="OTHER_OVERHEAD">Other Overhead</option>
          </select>
        </div>

        <div>
          <label className="mb-1 block font-medium text-slate-700">Description</label>
          <input
            type="text"
            required
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="e.g., Direct cooking & packing shift labour"
            className="w-full rounded-lg border border-slate-300 px-3 py-2"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block font-medium text-slate-700">Amount (INR)</label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              required
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 font-mono"
            />
          </div>
          <div>
            <label className="mb-1 block font-medium text-slate-700">Expense Date</label>
            <input
              type="date"
              required
              value={expenseDate}
              onChange={(e) => setExpenseDate(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2"
            />
          </div>
        </div>

        <label className="flex items-center gap-2 text-slate-700">
          <input
            type="checkbox"
            checked={autoPost}
            onChange={(e) => setAutoPost(e.target.checked)}
          />
          Post immediately to production run cost sheet
        </label>

        <button
          type="submit"
          disabled={saving}
          className="w-full rounded-lg bg-slate-900 px-4 py-2.5 font-medium text-white hover:bg-slate-800 disabled:opacity-50"
        >
          {saving ? "Saving..." : "Record Expense"}
        </button>
      </form>
    </div>
  );
}
