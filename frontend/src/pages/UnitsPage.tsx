import React, { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api, ApiError } from "../lib/api";
import { hasPermission } from "../lib/permissions";
import { Unit, UnitDimension } from "../types/masterData";
import {
  MasterFilterBar,
  PaginationFooter,
  StatusNotice,
} from "../components/MasterDataControls";

export function UnitsPage() {
  const { user } = useAuth();
  const canManage = hasPermission(user, "units:manage");

  const [units, setUnits] = useState<Unit[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const [search, setSearch] = useState("");
  const [dimensionFilter, setDimensionFilter] = useState<"" | UnitDimension>("");
  const [sortBy, setSortBy] = useState("symbol");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [symbol, setSymbol] = useState("");
  const [dimension, setDimension] = useState<UnitDimension>("mass");
  const [isBase, setIsBase] = useState(false);

  const loadUnits = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listUnits({
        search: search || undefined,
        dimension: dimensionFilter === "" ? undefined : dimensionFilter,
        sort_by: sortBy,
        sort_dir: sortDir,
        page,
        page_size: pageSize,
      });
      setUnits(res.items);
      setTotal(res.total);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load units.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadUnits();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, dimensionFilter, sortBy, sortDir, page]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    try {
      const created = await api.createUnit({
        name: name.trim(),
        symbol: symbol.trim().toLowerCase(),
        dimension,
        is_base: isBase,
        is_active: true,
      });
      setSuccess(`Created unit ${created.name} (${created.symbol}).`);
      setName("");
      setSymbol("");
      setIsBase(false);
      await loadUnits();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create unit.");
    }
  };

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">Units of Measure</h2>
        <p className="text-xs text-slate-500">
          Dimensional units (mass, volume, count) governing materials, products, and conversions.
        </p>
      </div>

      <StatusNotice error={error} success={success} />

      {canManage && (
        <form
          onSubmit={handleCreate}
          className="grid gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-5"
        >
          <input
            type="text"
            required
            placeholder="Unit Name (e.g. Box)"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-xs focus:border-slate-900 focus:outline-none"
          />
          <input
            type="text"
            required
            placeholder="Symbol (e.g. box)"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs focus:border-slate-900 focus:outline-none"
          />
          <select
            value={dimension}
            onChange={(e) => setDimension(e.target.value as UnitDimension)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs focus:border-slate-900 focus:outline-none"
          >
            <option value="mass">Mass</option>
            <option value="volume">Volume</option>
            <option value="count">Count</option>
          </select>
          <label className="flex items-center gap-2 px-2 text-xs text-slate-700">
            <input
              type="checkbox"
              checked={isBase}
              onChange={(e) => setIsBase(e.target.checked)}
              className="h-4 w-4 rounded border-slate-300"
            />
            Base Unit
          </label>
          <button
            type="submit"
            className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800"
          >
            <Plus className="h-3.5 w-3.5" /> Add Unit
          </button>
        </form>
      )}

      <MasterFilterBar
        search={search}
        onSearchChange={(v) => {
          setPage(1);
          setSearch(v);
        }}
        searchPlaceholder="Search unit name or symbol..."
        sortBy={sortBy}
        onSortByChange={setSortBy}
        sortOptions={[
          { value: "symbol", label: "Symbol" },
          { value: "name", label: "Name" },
          { value: "dimension", label: "Dimension" },
        ]}
        sortDir={sortDir}
        onSortDirChange={setSortDir}
        extraFilter={
          <select
            aria-label="Filter by dimension"
            value={dimensionFilter}
            onChange={(e) => {
              setPage(1);
              setDimensionFilter(e.target.value as "" | UnitDimension);
            }}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs focus:border-slate-900 focus:outline-none"
          >
            <option value="">All Dimensions</option>
            <option value="mass">Mass</option>
            <option value="volume">Volume</option>
            <option value="count">Count</option>
          </select>
        }
      />

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        {loading ? (
          <div className="p-8 text-center text-xs text-slate-500">Loading units...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Name</th>
                  <th className="px-4 py-3 font-medium">Symbol</th>
                  <th className="px-4 py-3 font-medium">Dimension</th>
                  <th className="px-4 py-3 font-medium">Base Unit</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {units.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-50/70">
                    <td className="px-4 py-3 font-medium text-slate-900">{u.name}</td>
                    <td className="px-4 py-3 font-mono text-slate-800">{u.symbol}</td>
                    <td className="px-4 py-3 uppercase text-slate-600">{u.dimension}</td>
                    <td className="px-4 py-3 text-slate-600">{u.is_base ? "Yes" : "No"}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium ${
                          u.is_active
                            ? "bg-emerald-50 text-emerald-700"
                            : "bg-slate-100 text-slate-500"
                        }`}
                      >
                        {u.is_active ? "Active" : "Inactive"}
                      </span>
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
