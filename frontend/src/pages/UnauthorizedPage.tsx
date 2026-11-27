import { Link } from "react-router-dom";
import { ShieldAlert } from "lucide-react";

export function UnauthorizedPage() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <div className="max-w-md rounded-xl border border-rose-200 bg-white p-8 text-center shadow-sm">
        <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-full bg-rose-50 text-rose-600">
          <ShieldAlert className="h-6 w-6" />
        </div>
        <h2 className="text-base font-semibold text-slate-900">
          Access Restricted by Role Policy
        </h2>
        <p className="mt-2 text-xs text-slate-600">
          Your current FactoryFlow role does not hold the required permission for this module.
        </p>
        <Link
          to="/dashboard"
          className="mt-5 inline-flex rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800"
        >
          Return to Role Workspace
        </Link>
      </div>
    </div>
  );
}
