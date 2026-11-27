import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { UserProfile } from "../types/auth";
import { CustomerType } from "../types/masterData";
import { StatusNotice } from "../components/MasterDataControls";

export function CustomerFormPage() {
  const { id } = useParams<{ id: string }>();
  const isEdit = Boolean(id);
  const navigate = useNavigate();

  const [salesmen, setSalesmen] = useState<UserProfile[]>([]);
  const [name, setName] = useState("");
  const [customerType, setCustomerType] = useState<CustomerType>("Retailer");
  const [gstin, setGstin] = useState("");
  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState("");
  const [city, setCity] = useState("");
  const [state, setState] = useState("Tamil Nadu");
  const [stateCode, setStateCode] = useState("33");
  const [salesmanId, setSalesmanId] = useState("");
  const [creditLimit, setCreditLimit] = useState("50000.00");
  const [isActive, setIsActive] = useState(true);

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        try {
          const usersRes = await api.listUsers();
          setSalesmen(usersRes.items);
        } catch {
          setSalesmen([]);
        }
        if (id) {
          const c = await api.getCustomer(id);
          setName(c.name);
          setCustomerType(c.customer_type);
          setGstin(c.gstin);
          setPhone(c.phone);
          setAddress(c.address);
          setCity(c.city);
          setState(c.state);
          setStateCode(c.state_code);
          setSalesmanId(c.assigned_salesman_id ?? "");
          setCreditLimit(String(c.credit_limit));
          setIsActive(c.is_active);
        }
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load customer.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [id]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const payload = {
        name: name.trim(),
        customer_type: customerType,
        gstin: gstin.trim().toUpperCase(),
        phone: phone.trim(),
        address: address.trim(),
        city: city.trim(),
        state: state.trim(),
        state_code: stateCode.trim(),
        assigned_salesman_id: salesmanId || null,
        credit_limit: creditLimit,
        is_active: isActive,
      };
      if (isEdit && id) {
        await api.updateCustomer(id, payload);
      } else {
        await api.createCustomer(payload);
      }
      navigate("/customers", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save customer.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
        Loading customer form...
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <div className="flex items-center gap-3">
        <Link
          to="/customers"
          className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Back
        </Link>
        <h2 className="text-lg font-semibold text-slate-900">
          {isEdit ? "Edit Customer" : "Add Customer"}
        </h2>
      </div>

      <StatusNotice error={error} />

      <form
        onSubmit={handleSubmit}
        className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Customer Name</label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs focus:border-slate-900 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Customer Type</label>
            <select
              value={customerType}
              onChange={(e) => setCustomerType(e.target.value as CustomerType)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs focus:border-slate-900 focus:outline-none"
            >
              <option value="Retailer">Retailer</option>
              <option value="Distributor">Distributor</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">GSTIN (15 chars)</label>
            <input
              type="text"
              required
              minLength={15}
              maxLength={15}
              value={gstin}
              onChange={(e) => setGstin(e.target.value.toUpperCase())}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs focus:border-slate-900 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Phone</label>
            <input
              type="text"
              required
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs focus:border-slate-900 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">City</label>
            <input
              type="text"
              required
              value={city}
              onChange={(e) => setCity(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs focus:border-slate-900 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">State</label>
            <input
              type="text"
              required
              value={state}
              onChange={(e) => setState(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs focus:border-slate-900 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">State Code</label>
            <input
              type="text"
              required
              value={stateCode}
              onChange={(e) => setStateCode(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs focus:border-slate-900 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Credit Limit (₹)</label>
            <input
              type="number"
              step="0.01"
              min="0"
              required
              value={creditLimit}
              onChange={(e) => setCreditLimit(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs focus:border-slate-900 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-700">Assigned Salesman</label>
            <select
              value={salesmanId}
              onChange={(e) => setSalesmanId(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs focus:border-slate-900 focus:outline-none"
            >
              <option value="">Unassigned</option>
              {salesmen.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.full_name} ({u.role})
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2 pt-5">
            <input
              id="cust-active"
              type="checkbox"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
              className="h-4 w-4 rounded border-slate-300"
            />
            <label htmlFor="cust-active" className="text-xs font-medium text-slate-700">
              Active customer
            </label>
          </div>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-700">Address</label>
          <textarea
            rows={2}
            required
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-xs focus:border-slate-900 focus:outline-none"
          />
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <Link
            to="/customers"
            className="rounded-lg border border-slate-300 px-4 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={submitting}
            className="rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
          >
            {submitting ? "Saving..." : isEdit ? "Update Customer" : "Create Customer"}
          </button>
        </div>
      </form>
    </div>
  );
}
