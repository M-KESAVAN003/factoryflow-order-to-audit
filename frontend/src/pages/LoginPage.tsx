import React, { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import {
  AlertCircle,
  CheckCircle2,
  Factory,
  Lock,
  ShieldCheck,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { ApiError } from "../lib/api";

const SEED_DEMO_ACCOUNTS = [
  { role: "Admin", email: "admin@factoryflow.io" },
  { role: "Order Mgr", email: "orders@factoryflow.io" },
  { role: "Floor Supv", email: "floor@factoryflow.io" },
  { role: "QA Insp", email: "qa@factoryflow.io" },
  { role: "Auditor", email: "auditor@factoryflow.io" },
  { role: "Owner", email: "owner@factoryflow.io" },
];

export function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (user) {
    return <Navigate to="/dashboard" replace />;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email.trim(), password);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Unable to reach FactoryFlow API. Ensure the backend server is running.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="grid min-h-screen bg-slate-50 lg:grid-cols-12">
      {/* Left Brand & Security Posture Panel */}
      <div className="flex flex-col justify-between bg-slate-950 p-8 text-slate-100 lg:col-span-5 lg:p-12">
        <div>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-sky-500/15 text-sky-400 ring-1 ring-sky-500/30">
              <Factory className="h-5 w-5" />
            </div>
            <div>
              <div className="text-base font-semibold tracking-tight text-white">
                FactoryFlow
              </div>
              <div className="text-xs uppercase tracking-widest text-slate-400">
                Order-to-Audit Platform
              </div>
            </div>
          </div>

          <div className="mt-12 space-y-4">
            <h1 className="text-2xl font-semibold leading-tight tracking-tight text-white lg:text-3xl">
              Controlled manufacturing execution from customer order to immutable audit.
            </h1>
            <p className="text-sm leading-relaxed text-slate-300">
              Sign in with your assigned operational identity. Every endpoint, view, and workflow transition is enforced by strict role-based access control and logged to Neon PostgreSQL.
            </p>
          </div>

          <div className="mt-10 space-y-3 border-t border-slate-800 pt-8 text-xs text-slate-300">
            <div className="flex items-center gap-2.5">
              <ShieldCheck className="h-4 w-4 text-emerald-400" />
              <span>RBAC separation of duties (Admin, Owner, Salesman/Order, Floor Supervisor, Auditor; plus optional QA Inspector)</span>
            </div>
            <div className="flex items-center gap-2.5">
              <Lock className="h-4 w-4 text-sky-400" />
              <span>JWT bearer session authentication with bcrypt credential hashing</span>
            </div>
            <div className="flex items-center gap-2.5">
              <CheckCircle2 className="h-4 w-4 text-indigo-400" />
              <span>Chronological audit trail for all sign-ins, denials, and role changes</span>
            </div>
          </div>
        </div>

        <div className="mt-10 border-t border-slate-800 pt-6 text-[11px] text-slate-400">
          Phase 1 Foundation &bull; FastAPI + SQLAlchemy + Neon PostgreSQL
        </div>
      </div>

      {/* Right Authentication Form */}
      <div className="flex items-center justify-center p-6 sm:p-10 lg:col-span-7">
        <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
          <div className="mb-6">
            <h2 className="text-xl font-semibold text-slate-900">
              Sign in to FactoryFlow
            </h2>
            <p className="mt-1 text-xs text-slate-500">
              Enter your corporate email and password to load your role workspace.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="email"
                className="mb-1.5 block text-xs font-medium text-slate-700"
              >
                Work Email
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                placeholder="name@factoryflow.io"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-slate-900 focus:outline-none focus:ring-1 focus:ring-slate-900"
              />
            </div>

            <div>
              <label
                htmlFor="password"
                className="mb-1.5 block text-xs font-medium text-slate-700"
              >
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-slate-900 focus:outline-none focus:ring-1 focus:ring-slate-900"
              />
            </div>

            {error && (
              <div
                role="alert"
                className="flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3.5 py-2.5 text-xs text-rose-700"
              >
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {submitting ? "Authenticating..." : "Sign in"}
            </button>
          </form>

          {/* Seeded account quick-fill helper (populates email only; still requires real password auth) */}
          <div className="mt-6 border-t border-slate-100 pt-5">
            <p className="mb-2 text-[11px] font-medium uppercase tracking-wider text-slate-400">
              Seeded Role Identifiers
            </p>
            <div className="flex flex-wrap gap-1.5">
              {SEED_DEMO_ACCOUNTS.map((acct) => (
                <button
                  key={acct.email}
                  type="button"
                  onClick={() => setEmail(acct.email)}
                  className="rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1 text-[11px] font-medium text-slate-700 hover:border-slate-300 hover:bg-slate-100"
                >
                  {acct.role}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
