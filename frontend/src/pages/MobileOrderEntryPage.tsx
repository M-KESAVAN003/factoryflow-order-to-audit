import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { CheckCircle2, Search } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { Customer, Product } from "../types/masterData";
import { StatusNotice } from "../components/MasterDataControls";

const FACTORY_STATE = "Tamil Nadu";

export function MobileOrderEntryPage() {
  const navigate = useNavigate();
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [customerId, setCustomerId] = useState("");
  const [productSearch, setProductSearch] = useState("");
  const [productId, setProductId] = useState("");
  const [quantity, setQuantity] = useState("150");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const [custRes, prodRes] = await Promise.all([
          api.listCustomers({ is_active: true, page_size: 100 }),
          api.listProducts({ is_active: true, page_size: 100 }),
        ]);
        setCustomers(custRes.items);
        setProducts(prodRes.items);
        if (custRes.items[0]) setCustomerId(custRes.items[0].id);
        const murukku = prodRes.items.find((p) => p.sku === "MUR-200") ?? prodRes.items[0];
        if (murukku) setProductId(murukku.id);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load customers and products.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

  const selectedCustomer = useMemo(
    () => customers.find((c) => c.id === customerId) ?? null,
    [customers, customerId]
  );
  const selectedProduct = useMemo(
    () => products.find((p) => p.id === productId) ?? null,
    [products, productId]
  );
  const filteredProducts = useMemo(() => {
    const q = productSearch.trim().toLowerCase();
    if (!q) return products;
    return products.filter(
      (p) => p.name.toLowerCase().includes(q) || p.sku.toLowerCase().includes(q)
    );
  }, [products, productSearch]);

  const preview = useMemo(() => {
    if (!selectedCustomer || !selectedProduct) {
      return { isIntra: true, taxable: 0, cgst: 0, sgst: 0, igst: 0, total: 0 };
    }
    const qty = Math.max(0, Number(quantity || 0));
    const price = Number(selectedProduct.selling_price);
    const rate = Number(selectedProduct.gst_rate);
    const taxable = Number((qty * price).toFixed(2));
    const isIntra =
      selectedCustomer.state.trim().toLowerCase() === FACTORY_STATE.toLowerCase();
    const cgst = isIntra ? Number(((taxable * (rate / 2)) / 100).toFixed(2)) : 0;
    const sgst = isIntra ? Number(((taxable * (rate / 2)) / 100).toFixed(2)) : 0;
    const igst = !isIntra ? Number(((taxable * rate) / 100).toFixed(2)) : 0;
    const total = Number((taxable + cgst + sgst + igst).toFixed(2));
    return { isIntra, taxable, cgst, sgst, igst, total };
  }, [selectedCustomer, selectedProduct, quantity]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!customerId || !productId) return;
    setSubmitting(true);
    setError(null);
    try {
      const created = await api.createSalesOrder({
        customer_id: customerId,
        notes: notes.trim() || null,
        items: [{ product_id: productId, quantity }],
      });
      navigate(`/sales/orders/${created.id}`, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to submit order.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
        Loading quick order form...
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-xl space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">Mobile Order Entry</h2>
        <p className="text-xs text-slate-500">
          Pick retailer or distributor, enter quantity, review live GST preview, and submit.
        </p>
      </div>

      <StatusNotice error={error} />

      <form
        onSubmit={handleSubmit}
        className="space-y-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5"
      >
        <div>
          <label className="mb-1.5 block text-xs font-medium text-slate-700">
            Assigned Customer
          </label>
          <select
            value={customerId}
            onChange={(e) => setCustomerId(e.target.value)}
            required
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm"
          >
            {customers.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} ({c.customer_type} — {c.state})
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="mb-1.5 block text-xs font-medium text-slate-700">
            Search Product
          </label>
          <div className="relative mb-2">
            <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-slate-400" />
            <input
              type="text"
              value={productSearch}
              onChange={(e) => setProductSearch(e.target.value)}
              placeholder="Search Murukku or SKU..."
              className="w-full rounded-lg border border-slate-300 py-2 pl-9 pr-3 text-sm"
            />
          </div>
          <select
            value={productId}
            onChange={(e) => setProductId(e.target.value)}
            required
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm"
          >
            {filteredProducts.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} ({p.sku}) — Rs {Number(p.selling_price).toFixed(2)} + {Number(p.gst_rate)}% GST
              </option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-700">
              Quantity ({selectedProduct?.unit_symbol ?? "packet"})
            </label>
            <input
              type="number"
              step="1"
              min="1"
              required
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2.5 font-mono text-sm"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-700">
              Unit Selling Price
            </label>
            <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 font-mono text-sm text-slate-800">
              Rs {selectedProduct ? Number(selectedProduct.selling_price).toFixed(2) : "0.00"}
            </div>
          </div>
        </div>

        <div>
          <label className="mb-1.5 block text-xs font-medium text-slate-700">Notes</label>
          <input
            type="text"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Delivery instruction (optional)"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
        </div>

        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3.5 text-xs space-y-1.5">
          <div className="flex justify-between text-slate-600">
            <span>Supply Type</span>
            <span className="font-semibold text-slate-900">
              {preview.isIntra ? "Intra-state (Tamil Nadu)" : `Inter-state (${selectedCustomer?.state})`}
            </span>
          </div>
          <div className="flex justify-between text-slate-600">
            <span>Taxable Subtotal</span>
            <span className="font-mono">Rs {preview.taxable.toFixed(2)}</span>
          </div>
          {preview.isIntra ? (
            <>
              <div className="flex justify-between text-slate-600">
                <span>CGST (2.5%)</span>
                <span className="font-mono">Rs {preview.cgst.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-slate-600">
                <span>SGST (2.5%)</span>
                <span className="font-mono">Rs {preview.sgst.toFixed(2)}</span>
              </div>
            </>
          ) : (
            <div className="flex justify-between text-slate-600">
              <span>IGST (5%)</span>
              <span className="font-mono">Rs {preview.igst.toFixed(2)}</span>
            </div>
          )}
          <div className="flex justify-between border-t border-slate-200 pt-1.5 text-sm font-semibold text-slate-900">
            <span>Estimated Total</span>
            <span className="font-mono">Rs {preview.total.toFixed(2)}</span>
          </div>
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-slate-900 px-4 py-3 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
        >
          <CheckCircle2 className="h-4 w-4" />
          {submitting ? "Submitting Order..." : "Submit Sales Order"}
        </button>
      </form>
    </div>
  );
}
