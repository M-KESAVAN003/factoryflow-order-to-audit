import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Plus, Trash2 } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { Product, StockItem, Unit } from "../types/masterData";
import { StatusNotice } from "../components/MasterDataControls";

interface BomLineFormRow {
  stock_item_id: string;
  standard_quantity: string;
  unit_id: string;
}

export function BomFormPage() {
  const { id } = useParams<{ id: string }>();
  const isEdit = Boolean(id);
  const navigate = useNavigate();

  const [products, setProducts] = useState<Product[]>([]);
  const [materials, setMaterials] = useState<StockItem[]>([]);
  const [units, setUnits] = useState<Unit[]>([]);

  const [productId, setProductId] = useState("");
  const [batchSize, setBatchSize] = useState("1");
  const [expectedOutput, setExpectedOutput] = useState("200");
  const [outputUnitId, setOutputUnitId] = useState("");
  const [effectiveDate, setEffectiveDate] = useState(new Date().toISOString().slice(0, 10));
  const [activate, setActivate] = useState(true);
  const [notes, setNotes] = useState("");
  const [lines, setLines] = useState<BomLineFormRow[]>([]);

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const [prodRes, rmRes, pkgRes, unitRes] = await Promise.all([
          api.listProducts({ page_size: 100 }),
          api.listRawMaterials({ page_size: 100 }),
          api.listPackagingMaterials({ page_size: 100 }),
          api.listUnits({ page_size: 100 }),
        ]);
        const combined = [...rmRes.items, ...pkgRes.items];
        setProducts(prodRes.items);
        setMaterials(combined);
        setUnits(unitRes.items);

        if (id) {
          const bom = await api.getBom(id);
          setProductId(bom.product_id);
          setBatchSize(String(bom.batch_size));
          setExpectedOutput(String(bom.expected_output));
          setOutputUnitId(bom.output_unit_id);
          setEffectiveDate(bom.effective_date);
          setNotes(bom.notes ?? "");
          setLines(
            bom.lines.map((l) => ({
              stock_item_id: l.stock_item_id,
              standard_quantity: String(l.standard_quantity),
              unit_id: l.unit_id,
            }))
          );
        } else {
          if (prodRes.items[0]) {
            setProductId(prodRes.items[0].id);
            setOutputUnitId(prodRes.items[0].unit_id);
          }
          if (combined[0]) {
            setLines([
              {
                stock_item_id: combined[0].id,
                standard_quantity: "10",
                unit_id: combined[0].base_unit_id,
              },
            ]);
          }
        }
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load BOM form.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [id]);

  const addLine = () => {
    if (!materials[0]) return;
    setLines((prev) => [
      ...prev,
      {
        stock_item_id: materials[0].id,
        standard_quantity: "1",
        unit_id: materials[0].base_unit_id,
      },
    ]);
  };

  const updateLine = (idx: number, patch: Partial<BomLineFormRow>) => {
    setLines((prev) =>
      prev.map((row, i) => {
        if (i !== idx) return row;
        const next = { ...row, ...patch };
        if (patch.stock_item_id) {
          const found = materials.find((m) => m.id === patch.stock_item_id);
          if (found) next.unit_id = found.base_unit_id;
        }
        return next;
      })
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      if (isEdit && id) {
        const updated = await api.updateBom(id, {
          batch_size: batchSize,
          expected_output: expectedOutput,
          output_unit_id: outputUnitId,
          effective_date: effectiveDate,
          notes: notes.trim() || null,
          lines,
        });
        navigate(`/boms/${updated.id}`, { replace: true });
      } else {
        const created = await api.createBom({
          product_id: productId,
          batch_size: batchSize,
          expected_output: expectedOutput,
          output_unit_id: outputUnitId,
          effective_date: effectiveDate,
          notes: notes.trim() || null,
          activate,
          lines,
        });
        navigate(`/boms/${created.id}`, { replace: true });
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save BOM.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
        Loading BOM editor...
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <div className="flex items-center gap-3">
        <Link
          to="/boms"
          className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Back
        </Link>
        <h2 className="text-lg font-semibold text-slate-900">
          {isEdit ? "Edit Draft BOM" : "Create New BOM Version"}
        </h2>
      </div>

      <StatusNotice error={error} />

      <form
        onSubmit={handleSubmit}
        className="space-y-5 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
      >
        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Finished Product</label>
            <select
              required
              disabled={isEdit}
              value={productId}
              onChange={(e) => {
                setProductId(e.target.value);
                const prod = products.find((p) => p.id === e.target.value);
                if (prod) setOutputUnitId(prod.unit_id);
              }}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs disabled:bg-slate-100"
            >
              {products.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.sku})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Batch Size</label>
            <input
              type="number"
              step="0.000001"
              min="0.000001"
              required
              value={batchSize}
              onChange={(e) => setBatchSize(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Expected Output</label>
            <input
              type="number"
              step="0.000001"
              min="0.000001"
              required
              value={expectedOutput}
              onChange={(e) => setExpectedOutput(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Output Unit</label>
            <select
              required
              value={outputUnitId}
              onChange={(e) => setOutputUnitId(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs"
            >
              {units.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.symbol}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Effective Date</label>
            <input
              type="date"
              required
              value={effectiveDate}
              onChange={(e) => setEffectiveDate(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs"
            />
          </div>
          {!isEdit && (
            <div className="flex items-center gap-2 pt-5">
              <input
                id="bom-activate"
                type="checkbox"
                checked={activate}
                onChange={(e) => setActivate(e.target.checked)}
                className="h-4 w-4 rounded border-slate-300"
              />
              <label htmlFor="bom-activate" className="text-xs font-medium text-slate-700">
                Activate immediately
              </label>
            </div>
          )}
        </div>

        <div className="space-y-3 border-t border-slate-100 pt-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-900">
              Standard Input Materials & Packaging
            </h3>
            <button
              type="button"
              onClick={addLine}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
            >
              <Plus className="h-3.5 w-3.5" /> Add Input
            </button>
          </div>

          {lines.map((row, idx) => (
            <div
              key={idx}
              className="grid gap-2 rounded-lg border border-slate-200 bg-slate-50 p-3 sm:grid-cols-12"
            >
              <div className="sm:col-span-6">
                <select
                  value={row.stock_item_id}
                  onChange={(e) => updateLine(idx, { stock_item_id: e.target.value })}
                  className="w-full rounded border border-slate-300 bg-white px-2.5 py-1.5 text-xs"
                >
                  {materials.map((m) => (
                    <option key={m.id} value={m.id}>
                      [{m.item_type}] {m.name} ({m.sku})
                    </option>
                  ))}
                </select>
              </div>
              <div className="sm:col-span-3">
                <input
                  type="number"
                  step="0.000001"
                  min="0.000001"
                  required
                  value={row.standard_quantity}
                  onChange={(e) => updateLine(idx, { standard_quantity: e.target.value })}
                  className="w-full rounded border border-slate-300 bg-white px-2.5 py-1.5 font-mono text-xs"
                />
              </div>
              <div className="sm:col-span-2">
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
              <div className="flex items-center justify-end sm:col-span-1">
                <button
                  type="button"
                  disabled={lines.length <= 1}
                  onClick={() => setLines((prev) => prev.filter((_, i) => i !== idx))}
                  className="rounded p-1.5 text-rose-600 hover:bg-rose-50 disabled:opacity-30"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-700">Formulation Notes</label>
          <input
            type="text"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs"
          />
        </div>

        <div className="flex justify-end gap-2">
          <Link
            to="/boms"
            className="rounded-lg border border-slate-300 px-4 py-2 text-xs font-medium text-slate-700"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={submitting}
            className="rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
          >
            {submitting ? "Saving..." : isEdit ? "Update Draft BOM" : "Create BOM Version"}
          </button>
        </div>
      </form>
    </div>
  );
}
