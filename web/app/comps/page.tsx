"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api, type LeaseComp, type SaleComp } from "@/lib/api";
import Cursor from "@/components/Cursor";

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

  if (error) return <p className="mx-auto max-w-6xl px-6 py-10 text-sm text-red-400">{error}</p>;
  if (!comp)
    return (
      <p className="mx-auto flex max-w-6xl items-center px-6 py-10 text-sm text-dim">
        loading
        <Cursor className="ml-2" />
      </p>
    );

  const isSale = type === "sale";
  const sale = isSale ? (comp as SaleComp) : null;
  const lease = !isSale ? (comp as LeaseComp) : null;

  return (
    <div className="mx-auto grid max-w-6xl grid-cols-1 gap-8 px-6 py-10 lg:grid-cols-2">
      <div>
        <p className="text-xs uppercase tracking-wide text-dim">
          {isSale ? "Sale comp" : "Lease comp"}
        </p>
        <h1 className="mt-1 flex items-center text-xl font-medium">
          {comp.address}
          <Cursor className="ml-2" />
        </h1>
        <p className="mt-1 text-sm text-dim">
          {[comp.city, comp.state].filter(Boolean).join(", ")}
        </p>

        <dl className="mt-6 grid grid-cols-2 gap-y-4 text-sm">
          <Field label="Submarket" value={comp.submarket ?? "—"} />
          <Field label="Property type" value={comp.property_type} className="capitalize" />
          <Field
            label="Building size"
            value={comp.building_sf ? `${comp.building_sf.toLocaleString()} SF` : "—"}
          />
          <Field
            label="Lot size"
            value={comp.lot_sf ? `${comp.lot_sf.toLocaleString()} SF` : "—"}
          />
          <Field label="Zoning" value={comp.zoning ?? "—"} />
          <Field label="Date received" value={comp.date_received} />

          {sale && (
            <>
              <Field label="Price" value={sale.price ? `$${sale.price.toLocaleString()}` : "—"} />
              <Field
                label="Price / SF"
                value={sale.price_per_sf ? `$${sale.price_per_sf.toFixed(2)}` : "—"}
              />
              <Field label="Cap rate" value={sale.cap_rate ? `${sale.cap_rate}%` : "—"} />
              {sale.num_units != null && (
                <Field label="Units" value={sale.num_units.toLocaleString()} />
              )}
              {sale.price_per_unit != null && (
                <Field
                  label="Price / unit"
                  value={`$${sale.price_per_unit.toLocaleString()}`}
                />
              )}
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
            <p className="text-xs uppercase tracking-wide text-dim">Notes</p>
            <p className="mt-1 text-sm">{comp.notes}</p>
          </div>
        )}
      </div>

      <div className="border border-line bg-accent/[0.03]">
        {flyerUrl ? (
          <iframe src={flyerUrl} className="h-[80vh] w-full" title="Original flyer" />
        ) : (
          <p className="flex items-center p-6 text-sm text-dim">
            loading_flyer
            <Cursor className="ml-2" />
          </p>
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
      <dt className="text-xs uppercase tracking-wide text-dim">{label}</dt>
      <dd className={`mt-0.5 ${className ?? ""}`}>{value}</dd>
    </div>
  );
}
