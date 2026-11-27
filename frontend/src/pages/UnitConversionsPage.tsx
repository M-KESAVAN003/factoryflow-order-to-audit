import React, { useEffect, useState } from "react";
import { ArrowRightLeft, Plus } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api, ApiError } from "../lib/api";
import { hasPermission } from "../lib/permissions";
import {
  Product,
  Unit,
  UnitConversion,
  UnitConvertResponse,
} from "../types/masterData";
import { StatusNotice } from "../components/MasterDataControls";

export function UnitConversionsPage() {
  const { user } = useAuth();
  const canManage = hasPermission(user, "units:manage");
  const canReadProducts = hasPermission(user, "products:read");

  const [conversions, setConversions] = useState<UnitConversion[]>([]);
  const [units, setUnits] = useState<Unit[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [fromUnitId, setFromUnitId] = useState("");
  const [toUnitId, setToUnitId] = useState("");
  const [productId, setProductId] = useState("");
  const [factor, setFactor] = useState("1000");

  // Live conversion verifier
  const [calcQty, setCalcQty] = useState("1");
  const [calcFromId, setCalcFromId] = useState("");
  const [calcToId, setCalcToId] = useState("");
  const [calcProductId, setCalcProductId] = useState("");
  const [calcResult, setCalcResult] = useState<UnitConvertResponse | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [convRes, unitRes] = await Promise.all([
        api.listUnitConversions({ page_size: 100 }),
        api.listUnits({ page_size: 100 }),
      ]);
      setConversions(convRes.items);
      setUnits(unitRes.items);

      if (unitRes.items.length >= 2 && !fromUnitId) {
        setFromUnitId(unitRes.items[0].id);
        setToUnitId(unitRes.items[1].id);
        setCalcFromId(unitRes.items[0].id);
        setCalcToId(unitRes.items[1].id);
      }

      if (canReadProducts) {
        const prodRes = await api.listProducts({ page_size: 100 });
        setProducts(prodRes.items);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load unit conversions.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    try {
      const created = await api.createUnitConversion({
        from_unit_id: fromUnitId,
        to_unit_id: toUnitId,
        product_id: productId || null,
        conversion_factor: factor,
        is_active: true,
      });
      setSuccess(
        `Added rule: 1 ${created.from_unit_symbol} = ${created.conversion_factor} ${created.to_unit_symbol}`
      );
      await loadData();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create conversion rule.");
    }
  };

  const handleCalculate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const res = await api.convertUnitQuantity({
        quantity: calcQty,
        from_unit_id: calcFromId,
        to_unit_id: calcToId,
        product_id: calcProductId || null,
      });
      setCalcResult(res);
    } catch (err) {
      setCalcResult(null);
      setError(err instanceof ApiError ? err.message : "Conversion rejected.");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">Unit Conversions</h2>
        <p className="text-xs text-slate-500">
          Dimension-validated conversion factors using exact Decimal arithmetic (global and product packaging rules).
        </p>
      </div>

      <StatusNotice error={error} success={success} />

      {canManage && (
        <form
          onSubmit={handleCreate}
          className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-5"
        >
          <select
            aria-label="From unit"
            value={fromUnitId}
            onChange={(e) => setFromUnitId(e.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs"
          >
            {units.map((u) => (
              <option key={u.id} value={u.id}>
                From: {u.symbol} ({u.dimension})
              </option>
            ))}
          </select>
          <select
            aria-label="To unit"
            value={toUnitId}
            onChange={(e) => setToUnitId(e.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs"
          >
            {units.map((u) => (
              <option key={u.id} value={u.id}>
                To: {u.symbol} ({u.dimension})
              </option>
            ))}
          </select>
          <input
            type="number"
            step="0.000001"
            min="0.000001"
            required
            placeholder="Factor"
            value={factor}
            onChange={(e) => setFactor(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs"
          />
          <select
            aria-label="Optional product scope"
            value={productId}
            onChange={(e) => setProductId(e.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs"
          >
            <option value="">Global Rule</option>
            {products.map((p) => (
              <option key={p.id} value={p.id}>
                Product: {p.name}
              </option>
            ))}
          </select>
          <button
            type="submit"
            className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800"
          >
            <Plus className="h-3.5 w-3.5" /> Add Rule
          </button>
        </form>
      )}

      {/* Interactive Decimal Conversion Tester */}
      <form
        onSubmit={handleCalculate}
        className="rounded-xl border border-sky-200 bg-sky-50/50 p-4 shadow-sm"
      >
        <div className="mb-3 flex items-center gap-2 text-xs font-semibold text-slate-900">
          <ArrowRightLeft className="h-4 w-4 text-sky-700" />
          Live Dimensional Conversion Calculator
        </div>
        <div className="grid gap-3 sm:grid-cols-5">
          <input
            type="number"
            step="0.000001"
            min="0.000001"
            required
            value={calcQty}
            onChange={(e) => setCalcQty(e.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 font-mono text-xs"
          />
          <select
            value={calcFromId}
            onChange={(e) => setCalcFromId(e.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs"
          >
            {units.map((u) => (
              <option key={u.id} value={u.id}>
                {u.symbol} ({u.dimension})
              </option>
            ))}
          </select>
          <select
            value={calcToId}
            onChange={(e) => setCalcToId(e.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs"
          >
            {units.map((u) => (
              <option key={u.id} value={u.id}>
                {u.symbol} ({u.dimension})
              </option>
            ))}
          </select>
          <select
            value={calcProductId}
            onChange={(e) => setCalcProductId(e.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs"
          >
            <option value="">Global Scope</option>
            {products.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
          <button
            type="submit"
            className="rounded-lg bg-sky-700 px-4 py-2 text-xs font-semibold text-white hover:bg-sky-800"
          >
            Convert
          </button>
        </div>
        {calcResult && (
          <p className="mt-3 font-mono text-xs font-medium text-slate-900">
            {calcResult.input_quantity} {calcResult.from_unit_symbol} ={" "}
            {calcResult.converted_quantity} {calcResult.to_unit_symbol} (factor{" "}
            {calcResult.factor_applied})
          </p>
        )}
      </form>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        {loading ? (
          <div className="p-8 text-center text-xs text-slate-500">
            Loading unit conversion rules...
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Conversion Rule</th>
                  <th className="px-4 py-3 font-medium">Dimension</th>
                  <th className="px-4 py-3 font-medium">Product Scope</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {conversions.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-50/70">
                    <td className="px-4 py-3 font-mono font-medium text-slate-900">
                      1 {c.from_unit_symbol} = {Number(c.conversion_factor)} {c.to_unit_symbol}
                    </td>
                    <td className="px-4 py-3 uppercase text-slate-600">
                      {c.from_unit_dimension}
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      {c.product_name ?? "Global"}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium ${
                          c.is_active
                            ? "bg-emerald-50 text-emerald-700"
                            : "bg-slate-100 text-slate-500"
                        }`}
                      >
                        {c.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
