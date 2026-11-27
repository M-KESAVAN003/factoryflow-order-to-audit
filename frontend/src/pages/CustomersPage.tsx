import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Edit2, Plus, Power } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api, ApiError } from "../lib/api";
import { hasPermission } from "../lib/permissions";
import { Customer, CustomerType } from "../types/masterData";
import {
  ConfirmDialog,
  MasterFilterBar,
  PaginationFooter,
  StatusNotice,
} from "../components/MasterDataControls";

export function CustomersPage() {
  const { user } = useAuth();
  const canManage = hasPermission(user, "customers:manage");

  const [items, setItems] = useState<Customer[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 10;

  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<"" | CustomerType>("");
  const [statusFilter, setStatusFilter] = useState("");
  const [sortBy, setSortBy] = useState("name");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [toggleTarget, setToggleTarget] = useState<Customer | null>(null);

  const loadCustomers = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listCustomers({
        search: search || undefined,
        customer_type: typeFilter === "" ? undefined : typeFilter,
        is_active: statusFilter === "" ? undefined : statusFilter === "true",
        sort_by: sortBy,
        sort_dir: sortDir,
        page,
        page_size: pageSize,
      });
      setItems(res.items);
      setTotal(res.total);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load customers.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadCustomers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, typeFilter, statusFilter, sortBy, sortDir, page]);

  const handleConfirmToggle = async () => {
    if (!toggleTarget) return;
    try {
      const updated = await api.updateCustomer(toggleTarget.id, {
        is_active: !toggleTarget.is_active,
      });
      setSuccess(
        `${updated.name} is now ${updated.is_active ? "Active" : "Inactive"}.`
      );
      setToggleTarget(null);
      await loadCustomers();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update customer.");
      setToggleTarget(null);
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Customers</h2>
          <p className="text-xs text-slate-500">
            Retailers and distributors with GSTIN, credit limits, and salesman assignment.
          </p>
        </div>
        {canManage && (
          <Link
            to="/customers/new"
            className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3.5 py-2 text-xs font-semibold text-white hover:bg-slate-800"
          >
            <Plus className="h-3.5 w-3.5" /> Add Customer
          </Link>
        )}
      </div>

      <StatusNotice error={error} success={success} />

      <MasterFilterBar
        search={search}
        onSearchChange={(v) => {
          setPage(1);
          setSearch(v);
        }}
        searchPlaceholder="Search customer name, GSTIN, or city..."
        statusFilter={statusFilter}
        onStatusFilterChange={(v) => {
          setPage(1);
          setStatusFilter(v);
        }}
        sortBy={sortBy}
        onSortByChange={setSortBy}
        sortOptions={[
          { value: "name", label: "Name" },
          { value: "city", label: "City" },
          { value: "state", label: "State" },
          { value: "credit_limit", label: "Credit Limit" },
        ]}
        sortDir={sortDir}
        onSortDirChange={setSortDir}
        extraFilter={
          <select
            aria-label="Filter by customer type"
            value={typeFilter}
            onChange={(e) => {
              setPage(1);
              setTypeFilter(e.target.value as "" | CustomerType);
            }}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs focus:border-slate-900 focus:outline-none"
          >
            <option value="">All Types</option>
            <option value="Retailer">Retailer</option>
            <option value="Distributor">Distributor</option>
          </select>
        }
      />

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        {loading ? (
          <div className="p-8 text-center text-xs text-slate-500">Loading customers...</div>
        ) : items.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500">No customers found.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-[11px] uppercase tracking-wider text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Customer</th>
                  <th className="px-4 py-3 font-medium">Type</th>
                  <th className="px-4 py-3 font-medium">GSTIN</th>
                  <th className="px-4 py-3 font-medium">Location</th>
                  <th className="px-4 py-3 font-medium">Salesman</th>
                  <th className="px-4 py-3 font-medium">Credit Limit (₹)</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  {canManage && <th className="px-4 py-3 font-medium">Actions</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {items.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-50/70">
                    <td className="px-4 py-3">
                      <div className="font-medium text-slate-900">{c.name}</div>
                      <div className="text-[11px] text-slate-500">{c.phone}</div>
                    </td>
                    <td className="px-4 py-3 text-slate-700">{c.customer_type}</td>
                    <td className="px-4 py-3 font-mono text-slate-800">{c.gstin}</td>
                    <td className="px-4 py-3 text-slate-600">
                      {c.city}, {c.state} ({c.state_code})
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      {c.assigned_salesman_name ?? "Unassigned"}
                    </td>
                    <td className="px-4 py-3 font-mono text-slate-900">
                      ₹{Number(c.credit_limit).toLocaleString()}
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
                    {canManage && (
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <Link
                            to={`/customers/${c.id}/edit`}
                            className="inline-flex items-center gap-1 rounded border border-slate-200 px-2 py-1 text-[11px] font-medium text-slate-700 hover:bg-slate-50"
                          >
                            <Edit2 className="h-3 w-3" /> Edit
                          </Link>
                          <button
                            type="button"
                            onClick={() => setToggleTarget(c)}
                            className="inline-flex items-center gap-1 rounded border border-slate-200 px-2 py-1 text-[11px] font-medium text-slate-700 hover:bg-slate-50"
                          >
                            <Power className="h-3 w-3" />
                            {c.is_active ? "Deactivate" : "Activate"}
                          </button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <PaginationFooter page={page} pageSize={pageSize} total={total} onPageChange={setPage} />
      </div>

      <ConfirmDialog
        open={toggleTarget !== null}
        title={toggleTarget?.is_active ? "Deactivate Customer" : "Activate Customer"}
        message={`Confirm changing active status for "${toggleTarget?.name ?? ""}"?`}
        confirmLabel="Confirm"
        onConfirm={() => void handleConfirmToggle()}
        onCancel={() => setToggleTarget(null)}
      />
    </div>
  );
}
