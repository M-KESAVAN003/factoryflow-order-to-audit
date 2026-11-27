import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Download } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { Invoice } from "../types/sales";
import { StatusNotice } from "../components/MasterDataControls";

export function InvoicePdfPreviewPage() {
  const { id } = useParams<{ id: string }>();
  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let activeUrl: string | null = null;
    const load = async () => {
      setLoading(true);
      try {
        const [inv, blob] = await Promise.all([api.getInvoice(id), api.downloadInvoicePdf(id)]);
        setInvoice(inv);
        activeUrl = URL.createObjectURL(blob);
        setPdfUrl(activeUrl);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load invoice PDF.");
      } finally {
        setLoading(false);
      }
    };
    void load();
    return () => {
      if (activeUrl) URL.revokeObjectURL(activeUrl);
    };
  }, [id]);

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Link
            to={id ? `/invoices/${id}` : "/invoices"}
            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Back
          </Link>
          <h2 className="text-lg font-semibold text-slate-900">
            GST Tax Invoice PDF {invoice ? `— ${invoice.invoice_number}` : ""}
          </h2>
        </div>
        {pdfUrl && invoice && (
          <a
            href={pdfUrl}
            download={`${invoice.invoice_number.replace(/\//g, "-")}.pdf`}
            className="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3 py-2 text-xs font-medium text-white"
          >
            <Download className="h-3.5 w-3.5" /> Download PDF
          </a>
        )}
      </div>

      <StatusNotice error={error} />

      {loading ? (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-xs text-slate-500">
          Rendering GST invoice PDF...
        </div>
      ) : pdfUrl ? (
        <iframe
          title="GST Invoice PDF"
          src={pdfUrl}
          className="h-[680px] w-full rounded-xl border border-slate-200 bg-white shadow-sm"
        />
      ) : null}
    </div>
  );
}
