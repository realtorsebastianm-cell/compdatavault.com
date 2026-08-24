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
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [exporting, setExporting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  useEffect(() => {
    setLoading(true);
    api
      .saleComps(toParams(filters))
      .then((next) => {
        setComps(next);
        // Drop any selection that's fallen out of the current filter view
        // rather than exporting a comp the user can no longer see.
        const stillPresent = new Set(next.map((c) => c.id));
        setSelected((prev) => new Set([...prev].filter((id) => stillPresent.has(id))));
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, [filters]);

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    setSelected((prev) =>
      prev.size === comps.length ? new Set() : new Set(comps.map((c) => c.id))
    );
  }

  async function handleExport() {
    setExporting(true);
    setError(null);
    try {
      await api.exportComps([...selected], []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    } finally {
      setExporting(false);
    }
  }

  async function handleBulkDelete() {
    if (!confirmingDelete) {
      setConfirmingDelete(true);
      return;
    }
    setDeleting(true);
    setError(null);
    const ids = [...selected];
    const results = await Promise.allSettled(ids.map((id) => api.deleteSaleComp(id)));
    const deletedIds = new Set(ids.filter((_, i) => results[i].status === "fulfilled"));
    const failedCount = ids.length - deletedIds.size;

    setComps((prev) => prev.filter((c) => !deletedIds.has(c.id)));
    setSelected((prev) => new Set([...prev].filter((id) => !deletedIds.has(id))));
    if (failedCount > 0) {
      setError(
        `${failedCount} of ${ids.length} comp${ids.length === 1 ? "" : "s"} couldn't be deleted -- try again`
      );
    }
    setConfirmingDelete(false);
    setDeleting(false);
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <div className="flex items-center justify-between">
        <h1 className="flex items-center text-xl font-medium">
          sale_vault
          <Cursor className="ml-2" />
        </h1>
        <div className="flex items-center gap-3">
          {selected.size > 0 && (
            <button
              onClick={handleExport}
              disabled={exporting}
              className="border border-line px-4 py-2 text-sm font-medium text-foreground hover:border-accent hover:text-accent disabled:cursor-not-allowed disabled:opacity-50"
            >
              {exporting ? "exporting..." : `export_${selected.size}`}
            </button>
          )}
          {selected.size > 0 && (
            <button
              onClick={handleBulkDelete}
              onBlur={() => setConfirmingDelete(false)}
              disabled={deleting}
              className={`border px-4 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50 ${
                confirmingDelete
                  ? "border-red-400 bg-red-400 text-background hover:bg-transparent hover:text-red-400"
                  : "border-line text-dim hover:border-red-400 hover:text-red-400"
              }`}
            >
              {deleting
                ? "deleting..."
                : confirmingDelete
                  ? "confirm_delete?"
                  : `delete_${selected.size}`}
            </button>
          )}
          <Link
            href="/upload"
            className="border border-accent px-4 py-2 text-sm font-medium text-accent hover:bg-accent hover:text-background"
          >
            upload_flyer
          </Link>
        </div>
      </div>

      <div className="mt-6">
        <VaultFilters filters={filters} onChange={setFilters} dealType="sale" />
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
                <th className="py-2 pr-2">
                  <input
                    type="checkbox"
                    checked={comps.length > 0 && selected.size === comps.length}
                    onChange={toggleAll}
                    aria-label="Select all"
                  />
                </th>
                <th className="py-2 pr-4">Address</th>
                <th className="py-2 pr-4">Submarket</th>
                <th className="py-2 pr-4">Type</th>
                <th className="py-2 pr-4">Building SF</th>
                <th className="py-2 pr-4">Lot SF</th>
                <th className="py-2 pr-4">Price</th>
                <th className="py-2 pr-4">$/SF</th>
                <th className="py-2 pr-4">$/Unit</th>
                <th className="py-2 pr-4">Cap rate</th>
                <th className="py-2 pr-4">Zoning</th>
                <th className="py-2 pr-4">Date</th>
              </tr>
            </thead>
            <tbody>
              {comps.map((c) => (
                <tr
                  key={c.id}
                  className="border-b border-line/60 hover:bg-accent/5"
                >
                  <td className="py-2 pr-2">
                    <input
                      type="checkbox"
                      checked={selected.has(c.id)}
                      onChange={() => toggle(c.id)}
                      aria-label={`Select ${c.address}`}
                    />
                  </td>
                  <td className="py-2 pr-4">
                    <Link
                      href={`/comps?type=sale&id=${c.id}`}
                      className="text-accent hover:underline"
                    >
                      {c.address}
                    </Link>
                    {c.duplicate_of_id && (
                      <span
                        className="ml-2 border border-amber-400/60 px-1 py-0.5 text-[10px] uppercase tracking-wide text-amber-400"
                        title="Possible duplicate of another comp in your vault"
                      >
                        dup
                      </span>
                    )}
                  </td>
                  <td className="py-2 pr-4">{c.submarket ?? "—"}</td>
                  <td className="py-2 pr-4 capitalize">{c.property_type}</td>
                  <td className="py-2 pr-4">
                    {c.building_sf ? c.building_sf.toLocaleString() : "—"}
                  </td>
                  <td className="py-2 pr-4">
                    {c.lot_sf ? c.lot_sf.toLocaleString() : "—"}
                  </td>
                  <td className="py-2 pr-4">
                    {c.price ? `$${c.price.toLocaleString()}` : "—"}
                  </td>
                  <td className="py-2 pr-4">
                    {c.price_per_sf ? `$${c.price_per_sf.toFixed(2)}` : "—"}
                  </td>
                  <td className="py-2 pr-4">
                    {c.price_per_unit ? `$${c.price_per_unit.toLocaleString()}` : "—"}
                  </td>
                  <td className="py-2 pr-4">
                    {c.cap_rate ? `${c.cap_rate}%` : "—"}
                  </td>
                  <td className="py-2 pr-4">{c.zoning ?? "—"}</td>
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
