"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type SaleComp } from "@/lib/api";
import VaultFilters, {
  EMPTY_FILTERS,
  toParams,
  type VaultFilterState,
} from "@/components/VaultFilters";
import Cursor from "@/components/Cursor";

export default function SaleVaultPage() {
  const [filters, setFilters] = useState<VaultFilterState>(EMPTY_FILTERS);
  const [comps, setComps] = useState<SaleComp[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    api
      .saleComps(toParams(filters))
      .then(setComps)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, [filters]);

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <div className="flex items-center justify-between">
        <h1 className="flex items-center text-xl font-medium">
          sale_vault
          <Cursor className="ml-2" />
        </h1>
        <Link
          href="/upload"
          className="border border-accent px-4 py-2 text-sm font-medium text-accent hover:bg-accent hover:text-background"
        >
          upload_flyer
        </Link>
      </div>

      <div className="mt-6">
        <VaultFilters filters={filters} onChange={setFilters} />
      </div>

      {error && <p className="mt-6 text-sm text-red-400">{error}</p>}
      {!loading && !error && comps.length === 0 && (
        <p className="mt-10 text-sm text-dim">
          No sale comps yet. Forward a flyer to your inbox address or upload
          one to get started.
        </p>
      )}

      {comps.length > 0 && (
        <div className="mt-6 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-line text-xs uppercase tracking-wide text-dim">
              <tr>
                <th className="py-2 pr-4">Address</th>
                <th className="py-2 pr-4">Submarket</th>
                <th className="py-2 pr-4">Type</th>
                <th className="py-2 pr-4">SF</th>
                <th className="py-2 pr-4">Price</th>
                <th className="py-2 pr-4">$/SF</th>
                <th className="py-2 pr-4">Cap rate</th>
                <th className="py-2 pr-4">Date</th>
              </tr>
            </thead>
            <tbody>
              {comps.map((c) => (
                <tr
                  key={c.id}
                  className="border-b border-line/60 hover:bg-accent/5"
                >
                  <td className="py-2 pr-4">
                    <Link
                      href={`/comps?type=sale&id=${c.id}`}
                      className="text-accent hover:underline"
                    >
                      {c.address}
                    </Link>
                  </td>
                  <td className="py-2 pr-4">{c.submarket ?? "—"}</td>
                  <td className="py-2 pr-4 capitalize">{c.property_type}</td>
                  <td className="py-2 pr-4">
                    {c.size_sf ? c.size_sf.toLocaleString() : "—"}
                  </td>
                  <td className="py-2 pr-4">
                    {c.price ? `$${c.price.toLocaleString()}` : "—"}
                  </td>
                  <td className="py-2 pr-4">
                    {c.price_per_sf ? `$${c.price_per_sf.toFixed(2)}` : "—"}
                  </td>
                  <td className="py-2 pr-4">
                    {c.cap_rate ? `${c.cap_rate}%` : "—"}
                  </td>
                  <td className="py-2 pr-4">{c.date_received}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
