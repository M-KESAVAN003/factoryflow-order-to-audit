import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { StockItemType, Unit } from "../types/masterData";
import { StatusNotice } from "../components/MasterDataControls";

export function StockItemFormPage({
  itemType,
  title,
  basePath,
}: {
  itemType: Extract<StockItemType, "RAW_MATERIAL" | "PACKAGING">;
  title: string;
  basePath: string;
}) {
  const { id } = useParams<{ id: string }>();
  const isEdit = Boolean(id);
  const navigate = useNavigate();

  const [units, setUnits] = useState<Unit[]>([]);
  const [name, setName] = useState("");
  const [sku, setSku] = useState("");
  const [baseUnitId, setBaseUnitId] = useState("");
  const [purchaseUnitId, setPurchaseUnitId] = useState("");
  const [purchaseRate, setPurchaseRate] = useState("0.00");
  const [reorderLevel, setReorderLevel] = useState("0.00");
  const [description, setDescription] = useState("");
  const [isActive, setIsActive] = useState(true);

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const unitRes = await api.listUnits({ page_size: 100 });
        setUnits(unitRes.items);

        if (id) {
          const item = await api.getStockItem(id);
          setName(item.name);
          setSku(item.sku);
          setBaseUnitId(item.base_unit_id);
          setPurchaseUnitId(item.purchase_unit_id);
          setPurchaseRate(String(item.purchase_rate));
          setReorderLevel(String(item.reorder_level));
          setDescription(item.description ?? "");
          setIsActive(item.is_active);
        } else {
          const defaultUnit =
            unitRes.items.find((u) =>
              itemType === "PACKAGING" ? u.symbol === "piece" : u.symbol === "kg"
            ) ?? unitRes.items[0];
          if (defaultUnit) {
            setBaseUnitId(defaultUnit.id);
            setPurchaseUnitId(defaultUnit.id);
          }
        }
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load form.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [id, itemType]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      if (isEdit && id) {
        await api.updateStockItem(id, {
          name: name.trim(),
          sku: sku.trim().toUpperCase(),
          base_unit_id: baseUnitId,
          purchase_unit_id: purchaseUnitId,
          purchase_rate: purchaseRate,
          reorder_level: reorderLevel,
          description: description.trim() || null,
          is_active: isActive,
        });
      } else {
        await api.createStockItem({
          name: name.trim(),
          sku: sku.trim().toUpperCase(),
          item_type: itemType,
          base_unit_id: baseUnitId,
          purchase_unit_id: purchaseUnitId,
          purchase_rate: purchaseRate,
          reorder_level: reorderLevel,
          description: description.trim() || null,
          is_active: isActive,
        });
      }
      navigate(basePath, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save stock item.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
        Loading form...
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <div className="flex items-center gap-3">
        <Link
          to={basePath}
          className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Back
        </Link>
        <h2 className="text-lg font-semibold text-slate-900">
          {isEdit ? `Edit ${title}` : `Add ${title}`}
        </h2>
      </div>

      <StatusNotice error={error} />

      <form
        onSubmit={handleSubmit}
        className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Item Name</label>
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
            <label className="mb-1 block text-xs font-medium text-slate-700">Base Unit</label>
            <select
              required
              value={baseUnitId}
              onChange={(e) => setBaseUnitId(e.target.value)}
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
            <label className="mb-1 block text-xs font-medium text-slate-700">Purchase Unit</label>
            <select
              required
              value={purchaseUnitId}
              onChange={(e) => setPurchaseUnitId(e.target.value)}
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
            <label className="mb-1 block text-xs font-medium text-slate-700">Purchase Rate (₹)</label>
            <input
              type="number"
              step="0.01"
              min="0"
              required
              value={purchaseRate}
              onChange={(e) => setPurchaseRate(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs focus:border-slate-900 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Reorder Level</label>
            <input
              type="number"
              step="0.01"
              min="0"
              required
              value={reorderLevel}
              onChange={(e) => setReorderLevel(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs focus:border-slate-900 focus:outline-none"
            />
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

        <div className="flex items-center gap-2">
          <input
            id="item-active"
            type="checkbox"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
            className="h-4 w-4 rounded border-slate-300"
          />
          <label htmlFor="item-active" className="text-xs font-medium text-slate-700">
            Active item
          </label>
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <Link
            to={basePath}
            className="rounded-lg border border-slate-300 px-4 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={submitting}
            className="rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
          >
            {submitting ? "Saving..." : isEdit ? "Update Item" : "Create Item"}
          </button>
        </div>
      </form>
    </div>
  );
}
