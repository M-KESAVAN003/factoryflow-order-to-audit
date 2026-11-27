import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Plus, Trash2 } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { PaymentStatus, PurchaseItemInput } from "../types/inventoryPurchase";
import { StockItem, Supplier, Unit } from "../types/masterData";
import { StatusNotice } from "../components/MasterDataControls";

export function PurchaseFormPage() {
  const { id } = useParams<{ id: string }>();
  const isEdit = Boolean(id);
  const navigate = useNavigate();

  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [stockItems, setStockItems] = useState<StockItem[]>([]);
  const [units, setUnits] = useState<Unit[]>([]);

  const [referenceNumber, setReferenceNumber] = useState(`PO-${Date.now().toString().slice(-6)}`);
  const [supplierId, setSupplierId] = useState("");
  const [purchaseDate, setPurchaseDate] = useState(new Date().toISOString().slice(0, 10));
  const [paymentStatus, setPaymentStatus] = useState<PaymentStatus>("UNPAID");
  const [notes, setNotes] = useState("");
  const [items, setItems] = useState<PurchaseItemInput[]>([]);

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadRefs = async () => {
      setLoading(true);
      try {
        const [supRes, itemRes, unitRes] = await Promise.all([
          api.listSuppliers({ is_active: true, page_size: 100 }),
          api.listStockItems({ is_active: true, page_size: 100 }),
          api.listUnits({ page_size: 100 }),
        ]);
        setSuppliers(supRes.items);
        setStockItems(itemRes.items);
        setUnits(unitRes.items);

        if (id) {
          const p = await api.getPurchase(id);
          setReferenceNumber(p.reference_number);
          setSupplierId(p.supplier_id);
          setPurchaseDate(p.purchase_date);
          setPaymentStatus(p.payment_status);
          setNotes(p.notes ?? "");
          setItems(
            p.items.map((li) => ({
              stock_item_id: li.stock_item_id,
              unit_id: li.unit_id,
              quantity: String(li.quantity),
              unit_rate: String(li.unit_rate),
              tax_rate: String(li.tax_rate),
            }))
          );
        } else {
          if (supRes.items[0]) setSupplierId(supRes.items[0].id);
          if (itemRes.items[0]) {
            setItems([
              {
                stock_item_id: itemRes.items[0].id,
                unit_id: itemRes.items[0].purchase_unit_id,
                quantity: "10",
                unit_rate: String(itemRes.items[0].purchase_rate),
                tax_rate: "0",
              },
            ]);
          }
        }
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load purchase form.");
      } finally {
        setLoading(false);
      }
    };
    void loadRefs();
  }, [id]);

  const addLine = () => {
    if (!stockItems[0]) return;
    setItems((prev) => [
      ...prev,
      {
        stock_item_id: stockItems[0].id,
        unit_id: stockItems[0].purchase_unit_id,
        quantity: "1",
        unit_rate: String(stockItems[0].purchase_rate),
        tax_rate: "0",
      },
    ]);
  };

  const updateLine = (idx: number, patch: Partial<PurchaseItemInput>) => {
    setItems((prev) =>
      prev.map((row, i) => {
        if (i !== idx) return row;
        const next = { ...row, ...patch };
        if (patch.stock_item_id) {
          const matched = stockItems.find((s) => s.id === patch.stock_item_id);
          if (matched) {
            next.unit_id = matched.purchase_unit_id;
            next.unit_rate = String(matched.purchase_rate);
          }
        }
        return next;
      })
    );
  };

  const estimatedTotals = items.reduce(
    (acc, row) => {
      const qty = Number(row.quantity || 0);
      const rate = Number(row.unit_rate || 0);
      const taxPct = Number(row.tax_rate || 0);
      const sub = qty * rate;
      const tax = (sub * taxPct) / 100;
      return {
        subtotal: acc.subtotal + sub,
        tax: acc.tax + tax,
        total: acc.total + sub + tax,
      };
    },
    { subtotal: 0, tax: 0, total: 0 }
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      if (isEdit && id) {
        const updated = await api.updatePurchase(id, {
          supplier_id: supplierId,
          purchase_date: purchaseDate,
          payment_status: paymentStatus,
          notes: notes.trim() || null,
          items,
        });
        navigate(`/purchases/${updated.id}`, { replace: true });
      } else {
        const created = await api.createPurchase({
          reference_number: referenceNumber.trim().toUpperCase(),
          supplier_id: supplierId,
          purchase_date: purchaseDate,
          payment_status: paymentStatus,
          notes: notes.trim() || null,
          items,
        });
        navigate(`/purchases/${created.id}`, { replace: true });
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save purchase.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
        Loading purchase form...
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <div className="flex items-center gap-3">
        <Link
          to="/purchases"
          className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Back
        </Link>
        <h2 className="text-lg font-semibold text-slate-900">
          {isEdit ? `Edit Draft Purchase (${referenceNumber})` : "New Purchase Draft"}
        </h2>
      </div>

      <StatusNotice error={error} />

      <form
        onSubmit={handleSubmit}
        className="space-y-5 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
      >
        <div className="grid gap-4 sm:grid-cols-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Reference Number</label>
            <input
              type="text"
              required
              disabled={isEdit}
              value={referenceNumber}
              onChange={(e) => setReferenceNumber(e.target.value.toUpperCase())}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs disabled:bg-slate-100"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Supplier</label>
            <select
              required
              value={supplierId}
              onChange={(e) => setSupplierId(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs"
            >
              {suppliers.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.state})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Purchase Date</label>
            <input
              type="date"
              required
              value={purchaseDate}
              onChange={(e) => setPurchaseDate(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Payment Status</label>
            <select
              value={paymentStatus}
              onChange={(e) => setPaymentStatus(e.target.value as PaymentStatus)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs"
            >
              <option value="UNPAID">Unpaid</option>
              <option value="PARTIAL">Partial</option>
              <option value="PAID">Paid</option>
            </select>
          </div>
        </div>

        <div className="space-y-3 border-t border-slate-100 pt-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-900">Purchase Items</h3>
            <button
              type="button"
              onClick={addLine}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
            >
              <Plus className="h-3.5 w-3.5" /> Add Item
            </button>
          </div>

          {items.map((row, idx) => (
            <div
              key={idx}
              className="grid gap-2 rounded-lg border border-slate-200 bg-slate-50 p-3 sm:grid-cols-12"
            >
              <div className="sm:col-span-4">
                <label className="mb-1 block text-[11px] text-slate-600">Item</label>
                <select
                  value={row.stock_item_id}
                  onChange={(e) => updateLine(idx, { stock_item_id: e.target.value })}
                  className="w-full rounded border border-slate-300 bg-white px-2.5 py-1.5 text-xs"
                >
                  {stockItems.map((si) => (
                    <option key={si.id} value={si.id}>
                      {si.name} ({si.sku})
                    </option>
                  ))}
                </select>
              </div>
              <div className="sm:col-span-2">
                <label className="mb-1 block text-[11px] text-slate-600">Unit</label>
                <select
                  value={row.unit_id}
                  onChange={(e) => updateLine(idx, { unit_id: e.target.value })}
                  className="w-full rounded border border-slate-300 bg-white px-2.5 py-1.5 text-xs"
                >
                  {units.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.symbol}
                    </option>
                  ))}
                </select>
              </div>
              <div className="sm:col-span-2">
                <label className="mb-1 block text-[11px] text-slate-600">Quantity</label>
                <input
                  type="number"
                  step="0.000001"
                  min="0.000001"
                  required
                  value={row.quantity}
                  onChange={(e) => updateLine(idx, { quantity: e.target.value })}
                  className="w-full rounded border border-slate-300 bg-white px-2.5 py-1.5 font-mono text-xs"
                />
              </div>
              <div className="sm:col-span-2">
                <label className="mb-1 block text-[11px] text-slate-600">Rate (₹)</label>
                <input
                  type="number"
                  step="0.0001"
                  min="0"
                  required
                  value={row.unit_rate}
                  onChange={(e) => updateLine(idx, { unit_rate: e.target.value })}
                  className="w-full rounded border border-slate-300 bg-white px-2.5 py-1.5 font-mono text-xs"
                />
              </div>
              <div className="sm:col-span-1">
                <label className="mb-1 block text-[11px] text-slate-600">Tax%</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max="28"
                  required
                  value={row.tax_rate}
                  onChange={(e) => updateLine(idx, { tax_rate: e.target.value })}
                  className="w-full rounded border border-slate-300 bg-white px-2 py-1.5 font-mono text-xs"
                />
              </div>
              <div className="flex items-end justify-end sm:col-span-1">
                <button
                  type="button"
                  disabled={items.length <= 1}
                  onClick={() => setItems((prev) => prev.filter((_, i) => i !== idx))}
                  className="rounded p-1.5 text-rose-600 hover:bg-rose-50 disabled:opacity-30"
                  aria-label="Remove line item"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-4 border-t border-slate-100 pt-4 text-xs">
          <div className="flex-1">
            <label className="mb-1 block text-xs font-medium text-slate-700">Notes</label>
            <input
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Optional purchase notes..."
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs"
            />
          </div>
          <div className="rounded-lg bg-slate-50 px-4 py-3 text-right font-mono">
            <div>Subtotal: ₹{estimatedTotals.subtotal.toFixed(2)}</div>
            <div>Tax: ₹{estimatedTotals.tax.toFixed(2)}</div>
            <div className="text-sm font-semibold text-slate-900">
              Total: ₹{estimatedTotals.total.toFixed(2)}
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-2">
          <Link
            to="/purchases"
            className="rounded-lg border border-slate-300 px-4 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={submitting}
            className="rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
          >
            {submitting ? "Saving Draft..." : isEdit ? "Save Changes" : "Save as Draft"}
          </button>
        </div>
      </form>
    </div>
  );
}
