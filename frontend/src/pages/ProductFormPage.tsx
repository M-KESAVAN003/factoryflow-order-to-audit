import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { StockItem, Unit } from "../types/masterData";
import { StatusNotice } from "../components/MasterDataControls";

export function ProductFormPage() {
  const { id } = useParams<{ id: string }>();
  const isEdit = Boolean(id);
  const navigate = useNavigate();

  const [units, setUnits] = useState<Unit[]>([]);
  const [packagingItems, setPackagingItems] = useState<StockItem[]>([]);

  const [name, setName] = useState("");
  const [sku, setSku] = useState("");
  const [category, setCategory] = useState("Savory Snacks");
  const [description, setDescription] = useState("");
  const [packSize, setPackSize] = useState("200 g");
  const [sellingPrice, setSellingPrice] = useState("50.00");
  const [gstRate, setGstRate] = useState("5.00");
  const [hsnCode, setHsnCode] = useState("19059090");
  const [unitId, setUnitId] = useState("");
  const [pouchId, setPouchId] = useState("");
  const [cartonId, setCartonId] = useState("");
  const [packetsPerCarton, setPacketsPerCarton] = useState(20);
  const [isActive, setIsActive] = useState(true);

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadRefs = async () => {
      setLoading(true);
      try {
        const [unitRes, pkgRes] = await Promise.all([
          api.listUnits({ page_size: 100 }),
          api.listPackagingMaterials({ page_size: 100 }),
        ]);
        setUnits(unitRes.items);
        setPackagingItems(pkgRes.items);

        if (id) {
          const prod = await api.getProduct(id);
          setName(prod.name);
          setSku(prod.sku);
          setCategory(prod.category);
          setDescription(prod.description ?? "");
          setPackSize(prod.pack_size);
          setSellingPrice(String(prod.selling_price));
          setGstRate(String(prod.gst_rate));
          setHsnCode(prod.hsn_code);
          setUnitId(prod.unit_id);
          setPouchId(prod.pouch_stock_item_id ?? "");
          setCartonId(prod.carton_stock_item_id ?? "");
          setPacketsPerCarton(prod.packets_per_carton);
          setIsActive(prod.is_active);
        } else {
          const pkt = unitRes.items.find((u) => u.symbol === "packet") ?? unitRes.items[0];
          if (pkt) setUnitId(pkt.id);
        }
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load product form.");
      } finally {
        setLoading(false);
      }
    };
    void loadRefs();
  }, [id]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const payload = {
        name: name.trim(),
        sku: sku.trim().toUpperCase(),
        category: category.trim(),
        description: description.trim() || null,
        pack_size: packSize.trim(),
        selling_price: sellingPrice,
        gst_rate: gstRate,
        hsn_code: hsnCode.trim(),
        unit_id: unitId,
        pouch_stock_item_id: pouchId || null,
        carton_stock_item_id: cartonId || null,
        packets_per_carton: Number(packetsPerCarton),
        is_active: isActive,
      };
      if (isEdit && id) {
        await api.updateProduct(id, payload);
      } else {
        await api.createProduct(payload);
      }
      navigate("/products", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save product.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
        Loading product form...
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <div className="flex items-center gap-3">
        <Link
          to="/products"
          className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Back
        </Link>
        <h2 className="text-lg font-semibold text-slate-900">
          {isEdit ? "Edit Product" : "Add New Product"}
        </h2>
      </div>

      <StatusNotice error={error} />

      <form
        onSubmit={handleSubmit}
        className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Product Name</label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs focus:border-slate-900 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">SKU</label>
            <input
              type="text"
              required
              value={sku}
              onChange={(e) => setSku(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs focus:border-slate-900 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Category</label>
            <input
              type="text"
              required
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs focus:border-slate-900 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Pack Size</label>
            <input
              type="text"
              required
              value={packSize}
              onChange={(e) => setPackSize(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs focus:border-slate-900 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Selling Price (₹)</label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              required
              value={sellingPrice}
              onChange={(e) => setSellingPrice(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs focus:border-slate-900 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">GST Rate (%)</label>
            <input
              type="number"
              step="0.01"
              min="0"
              max="28"
              required
              value={gstRate}
              onChange={(e) => setGstRate(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs focus:border-slate-900 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">HSN Code</label>
            <input
              type="text"
              required
              minLength={4}
              value={hsnCode}
              onChange={(e) => setHsnCode(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs focus:border-slate-900 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Base Unit</label>
            <select
              required
              value={unitId}
              onChange={(e) => setUnitId(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs focus:border-slate-900 focus:outline-none"
            >
              {units.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.name} ({u.symbol})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">
              Primary Pouch Packaging
            </label>
            <select
              value={pouchId}
              onChange={(e) => setPouchId(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs focus:border-slate-900 focus:outline-none"
            >
              <option value="">None</option>
              {packagingItems.map((pkg) => (
                <option key={pkg.id} value={pkg.id}>
                  {pkg.name} ({pkg.sku})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">
              Outer Carton Packaging
            </label>
            <select
              value={cartonId}
              onChange={(e) => setCartonId(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs focus:border-slate-900 focus:outline-none"
            >
              <option value="">None</option>
              {packagingItems.map((pkg) => (
                <option key={pkg.id} value={pkg.id}>
                  {pkg.name} ({pkg.sku})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">
              Packets per Carton
            </label>
            <input
              type="number"
              min={1}
              required
              value={packetsPerCarton}
              onChange={(e) => setPacketsPerCarton(Number(e.target.value))}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs focus:border-slate-900 focus:outline-none"
            />
          </div>
          <div className="flex items-center gap-2 pt-5">
            <input
              id="prod-active"
              type="checkbox"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
              className="h-4 w-4 rounded border-slate-300"
            />
            <label htmlFor="prod-active" className="text-xs font-medium text-slate-700">
              Active for production & orders
            </label>
          </div>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-700">Description</label>
          <textarea
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs focus:border-slate-900 focus:outline-none"
          />
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <Link
            to="/products"
            className="rounded-lg border border-slate-300 px-4 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={submitting}
            className="rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
          >
            {submitting ? "Saving..." : isEdit ? "Update Product" : "Create Product"}
          </button>
        </div>
      </form>
    </div>
  );
}
