"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api, type LeaseComp, type SaleComp } from "@/lib/api";

export default function CompDetailPage() {
  return (
    <Suspense fallback={null}>
      <CompDetail />
    </Suspense>
  );
}

function CompDetail() {
  const params = useSearchParams();
  const type = params.get("type");
  const id = params.get("id");

  const [comp, setComp] = useState<SaleComp | LeaseComp | null>(null);
  const [flyerUrl, setFlyerUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!type || !id) return;
    setError(null);
    setComp(null);

    const load =
      type === "sale" ? api.saleComp(id) : type === "lease" ? api.leaseComp(id) : null;
    if (!load) {
      setError("Unknown comp type");
      return;
    }
    load
      .then((c) => {
        setComp(c);
        return api.flyerFileBlobUrl(c.flyer_id);
      })
      .then(setFlyerUrl)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load"));
  }, [type, id]);

  if (error) return <p className="mx-auto max-w-6xl px-6 py-10 text-sm text-red-600">{error}</p>;
  if (!comp) return <p className="mx-auto max-w-6xl px-6 py-10 text-sm text-black/60 dark:text-white/60">Loading&hellip;</p>;

  const isSale = type === "sale";
  const sale = isSale ? (comp as SaleComp) : null;
  const lease = !isSale ? (comp as LeaseComp) : null;

  return (
    <div className="mx-auto grid max-w-6xl grid-cols-1 gap-8 px-6 py-10 lg:grid-cols-2">
      <div>
        <p className="text-xs uppercase tracking-wide text-black/50 dark:text-white/50">
          {isSale ? "Sale comp" : "Lease comp"}
        </p>
        <h1 className="mt-1 text-2xl font-semibold">{comp.address}</h1>
        <p className="mt-1 text-sm text-black/60 dark:text-white/60">
          {[comp.city, comp.state].filter(Boolean).join(", ")}
        </p>

        <dl className="mt-6 grid grid-cols-2 gap-y-4 text-sm">
          <Field label="Submarket" value={comp.submarket ?? "—"} />
          <Field label="Property type" value={comp.property_type} className="capitalize" />
          <Field
            label="Size"
            value={comp.size_sf ? `${comp.size_sf.toLocaleString()} SF` : "—"}
          />
          <Field label="Date received" value={comp.date_received} />

          {sale && (
            <>
              <Field label="Price" value={sale.price ? `$${sale.price.toLocaleString()}` : "—"} />
              <Field
                label="Price / SF"
                value={sale.price_per_sf ? `$${sale.price_per_sf.toFixed(2)}` : "—"}
              />
              <Field label="Cap rate" value={sale.cap_rate ? `${sale.cap_rate}%` : "—"} />
            </>
          )}

          {lease && (
            <>
              <Field
                label="Rate"
                value={lease.rate ? `$${lease.rate.toFixed(2)} (${lease.rate_type ?? "?"})` : "—"}
              />
              <Field
                label="Term"
                value={lease.term_months ? `${lease.term_months} months` : "—"}
              />
              <Field
                label="Expenses"
                value={lease.expense_type.replace("_", " ")}
                className="capitalize"
              />
            </>
          )}

          <Field label="Broker" value={comp.broker_name ?? "—"} />
          <Field label="Brokerage" value={comp.brokerage ?? "—"} />
        </dl>

        {comp.notes && (
          <div className="mt-6">
            <p className="text-xs uppercase tracking-wide text-black/50 dark:text-white/50">
              Notes
            </p>
            <p className="mt-1 text-sm">{comp.notes}</p>
          </div>
        )}
      </div>

      <div className="rounded-lg border border-black/10 bg-black/[0.02] dark:border-white/10 dark:bg-white/[0.02]">
        {flyerUrl ? (
          <iframe src={flyerUrl} className="h-[80vh] w-full rounded-lg" title="Original flyer" />
        ) : (
          <p className="p-6 text-sm text-black/60 dark:text-white/60">Loading flyer&hellip;</p>
        )}
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  className,
}: {
  label: string;
  value: string;
  className?: string;
}) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-black/50 dark:text-white/50">
        {label}
      </dt>
      <dd className={`mt-0.5 ${className ?? ""}`}>{value}</dd>
    </div>
  );
}
