import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Boxes,
  Building2,
  Package,
  Ruler,
  Scale,
  ShoppingBag,
  Users2,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api, ApiError } from "../lib/api";
import { hasPermission } from "../lib/permissions";
import { MasterDataSummary } from "../types/masterData";
import { StatusNotice } from "../components/MasterDataControls";

export function MasterDataDashboardPage() {
  const { user } = useAuth();
  const [summary, setSummary] = useState<MasterDataSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        setSummary(await api.masterDataSummary());
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load master data summary.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

  const cards = [
    {
      label: "Finished Products",
      count: summary?.products_total ?? 0,
      sub: `${summary?.products_active ?? 0} active SKUs`,
      to: "/products",
      perm: "products:read",
      icon: ShoppingBag,
    },
    {
      label: "Raw Materials",
      count: summary?.raw_materials_total ?? 0,
      sub: "Shared StockItem (RAW_MATERIAL)",
      to: "/raw-materials",
      perm: "stock_items:read",
      icon: Boxes,
    },
    {
      label: "Packaging Materials",
      count: summary?.packaging_materials_total ?? 0,
      sub: "Shared StockItem (PACKAGING)",
      to: "/packaging-materials",
      perm: "stock_items:read",
      icon: Package,
    },
    {
      label: "Suppliers",
      count: summary?.suppliers_total ?? 0,
      sub: "GST-verified vendors",
      to: "/suppliers",
      perm: "suppliers:read",
      icon: Building2,
    },
    {
      label: "Customers",
      count: summary?.customers_total ?? 0,
      sub: "Retailers & Distributors",
      to: "/customers",
      perm: "customers:read",
      icon: Users2,
    },
    {
      label: "Units of Measure",
      count: summary?.units_total ?? 0,
      sub: "Mass, volume & count units",
      to: "/units",
      perm: "units:read",
      icon: Ruler,
    },
    {
      label: "Unit Conversions",
      count: summary?.conversions_total ?? 0,
      sub: "Dimensional & pack rules",
      to: "/unit-conversions",
      perm: "units:read",
      icon: Scale,
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">
          Master Data Management
        </h2>
        <p className="text-xs text-slate-500">
          Central registry for finished products, unified stock items, partners, units, and dimensional conversions.
        </p>
      </div>

      <StatusNotice error={error} />

      {loading ? (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
          Loading master data counts...
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {cards.map((card) => {
            const Icon = card.icon;
            const allowed = hasPermission(user, card.perm);
            return (
              <div
                key={card.label}
                className="flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium uppercase tracking-wider text-slate-500">
                      {card.label}
                    </span>
                    <Icon className="h-4 w-4 text-slate-400" />
                  </div>
                  <p className="mt-2 text-2xl font-semibold text-slate-900 tabular-nums">
                    {card.count}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">{card.sub}</p>
                </div>

                <div className="mt-4 border-t border-slate-100 pt-3">
                  {allowed ? (
                    <Link
                      to={card.to}
                      className="text-xs font-semibold text-sky-700 hover:text-sky-800"
                    >
                      Open {card.label} →
                    </Link>
                  ) : (
                    <span className="text-[11px] text-slate-400">
                      Restricted for current role
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
