"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { api, type LeaseComp, type SaleComp } from "@/lib/api";
import Cursor from "@/components/Cursor";
import type { MapPoint } from "@/components/CompsMap";

// Leaflet touches `window` at import time, so it can't run during SSR --
// loaded client-only.
const CompsMap = dynamic(() => import("@/components/CompsMap"), {
  ssr: false,
  loading: () => (
    <div className="flex h-[70vh] w-full items-center justify-center border border-line text-sm text-dim">
      loading map
    </div>
  ),
});

export default function MapPage() {
  const [saleComps, setSaleComps] = useState<SaleComp[]>([]);
  const [leaseComps, setLeaseComps] = useState<LeaseComp[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [backfilling, setBackfilling] = useState(false);
  const [backfillNote, setBackfillNote] = useState<string | null>(null);

  function reload() {
    setLoading(true);
    setError(null);
    Promise.all([api.saleComps(), api.leaseComps()])
      .then(([sales, leases]) => {
        setSaleComps(sales);
        setLeaseComps(leases);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load"))
      .finally(() => setLoading(false));
  }

  useEffect(reload, []);

  async function handleBackfill() {
    setBackfilling(true);
    setBackfillNote(null);
    try {
      const result = await api.geocodeBackfill();
      setBackfillNote(
        `Geocoded ${result.geocoded}${result.failed ? `, ${result.failed} couldn't be located` : ""}` +
          (result.remaining > 0 ? ` -- ${result.remaining} more left, click again` : " -- all caught up")
      );
      reload();
    } catch (err) {
      setBackfillNote(err instanceof Error ? err.message : "Backfill failed");
    } finally {
      setBackfilling(false);
    }
  }

  const points: MapPoint[] = [
    ...saleComps
      .filter((c) => c.latitude != null && c.longitude != null)
      .map((c) => ({ dealType: "sale" as const, lat: c.latitude as number, lng: c.longitude as number, comp: c })),
    ...leaseComps
      .filter((c) => c.latitude != null && c.longitude != null)
      .map((c) => ({ dealType: "lease" as const, lat: c.latitude as number, lng: c.longitude as number, comp: c })),
  ];

  const missingCount =
    saleComps.filter((c) => c.latitude == null).length +
    leaseComps.filter((c) => c.latitude == null).length;

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <div className="flex items-center justify-between">
        <h1 className="flex items-center text-xl font-medium">
          map
          <Cursor className="ml-2" />
        </h1>
        <div className="flex items-center gap-4 text-xs">
          <span className="flex items-center gap-1.5 text-dim">
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-blue-600" />
            sale
          </span>
          <span className="flex items-center gap-1.5 text-dim">
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-green-600" />
            lease
          </span>
        </div>
      </div>
      <p className="mt-2 text-sm text-dim">
        Every comp in your vault with a geocoded address, plotted by
        location -- useful for spotting clusters or gaps in a submarket at
        a glance. Click a pin for details.
      </p>

      {missingCount > 0 && (
        <div className="mt-4 flex items-center gap-3 border border-line bg-accent/[0.03] px-4 py-3 text-sm">
          <p className="flex-1 text-dim">
            {missingCount} comp{missingCount === 1 ? "" : "s"} in your vault{" "}
            {missingCount === 1 ? "isn't" : "aren't"} on the map yet
            {saleComps.length + leaseComps.length > 0 &&
              " -- likely ingested before the map existed"}
            .
          </p>
          <button
            onClick={handleBackfill}
            disabled={backfilling}
            className="border border-accent px-3 py-1.5 text-xs font-medium text-accent hover:bg-accent hover:text-background disabled:cursor-not-allowed disabled:opacity-50"
          >
            {backfilling ? "geocoding..." : "geocode_missing"}
          </button>
        </div>
      )}
      {backfillNote && <p className="mt-2 text-xs text-dim">{backfillNote}</p>}

      {error && <p className="mt-4 text-sm text-red-400">{error}</p>}

      <div className="mt-6">
        {!loading && points.length === 0 ? (
          <p className="border border-line p-8 text-center text-sm text-dim">
            Nothing geocoded yet. Upload a flyer or click{" "}
            <span className="text-foreground">geocode_missing</span> above
            once you have comps in your vault.
          </p>
        ) : (
          <CompsMap points={points} />
        )}
      </div>
    </div>
  );
}
