"use client";

import { PROPERTY_TYPES, type PropertyType } from "@/lib/api";

export interface VaultFilterState {
  q: string;
  property_type: PropertyType | "";
  submarket: string;
  zoning: string;
  price_per_unit_min: string;
  price_per_unit_max: string;
  date_from: string;
  date_to: string;
}

export const EMPTY_FILTERS: VaultFilterState = {
  q: "",
  property_type: "",
  submarket: "",
  zoning: "",
  price_per_unit_min: "",
  price_per_unit_max: "",
  date_from: "",
  date_to: "",
};

export function toParams(filters: VaultFilterState): Record<string, string> {
  const params: Record<string, string> = {};
  if (filters.q) params.q = filters.q;
  if (filters.property_type) params.property_type = filters.property_type;
  if (filters.submarket) params.submarket = filters.submarket;
  // zoning and price-per-unit only mean anything for the property types
  // that use them, but the backend just ignores an empty/absent param, so
  // it's safe to send them whenever they're filled in.
  if (filters.zoning) params.zoning = filters.zoning;
  if (filters.price_per_unit_min) params.price_per_unit_min = filters.price_per_unit_min;
  if (filters.price_per_unit_max) params.price_per_unit_max = filters.price_per_unit_max;
  if (filters.date_from) params.date_from = filters.date_from;
  if (filters.date_to) params.date_to = filters.date_to;
  return params;
}

export default function VaultFilters({
  filters,
  onChange,
  dealType,
}: {
  filters: VaultFilterState;
  onChange: (next: VaultFilterState) => void;
  /** Lease comps don't have a price-per-unit field at all -- only show
   * that filter on the sale vault. Defaults to "sale" so nothing breaks
   * if a caller doesn't pass it. */
  dealType?: "sale" | "lease";
}) {
  function set<K extends keyof VaultFilterState>(key: K, value: VaultFilterState[K]) {
    onChange({ ...filters, [key]: value });
  }

  const inputClass =
    "border border-line bg-transparent px-2 py-1.5 text-sm text-foreground focus:border-accent focus:outline-none";

  const isMultifamily = filters.property_type === "multifamily" && dealType !== "lease";
  const isIndustrial = filters.property_type === "industrial";

  const hasAnyFilter =
    filters.q ||
    filters.property_type ||
    filters.submarket ||
    filters.zoning ||
    filters.price_per_unit_min ||
    filters.price_per_unit_max ||
    filters.date_from ||
    filters.date_to;

  return (
    <div className="flex flex-wrap items-end gap-3">
      <label className="flex flex-col gap-1 text-xs text-dim">
        address
        <input
          value={filters.q}
          onChange={(e) => set("q", e.target.value)}
          placeholder="search"
          className={inputClass}
        />
      </label>

      {/* property_type sits right after address -- it's the field that
          decides which other filters show up below, so it's the main
          thing to set first. */}
      <label className="flex flex-col gap-1 text-xs text-dim">
        property_type
        <select
          value={filters.property_type}
          onChange={(e) => {
            const next = e.target.value as PropertyType | "";
            // Clear out filters that don't apply to the newly selected
            // type, so e.g. a leftover zoning filter doesn't silently keep
            // narrowing results after switching away from industrial.
            onChange({
              ...filters,
              property_type: next,
              zoning: next === "industrial" ? filters.zoning : "",
              price_per_unit_min: next === "multifamily" ? filters.price_per_unit_min : "",
              price_per_unit_max: next === "multifamily" ? filters.price_per_unit_max : "",
            });
          }}
          className={inputClass}
        >
          <option value="">any</option>
          {PROPERTY_TYPES.map((pt) => (
            <option key={pt} value={pt}>
              {pt}
            </option>
          ))}
        </select>
      </label>

      <label className="flex flex-col gap-1 text-xs text-dim">
        submarket
        <input
          value={filters.submarket}
          onChange={(e) => set("submarket", e.target.value)}
          placeholder="any"
          className={inputClass}
        />
      </label>

      {/* Multifamily sale comps get evaluated per-unit, not per-SF. */}
      {isMultifamily && (
        <>
          <label className="flex flex-col gap-1 text-xs text-dim">
            $/unit min
            <input
              type="number"
              value={filters.price_per_unit_min}
              onChange={(e) => set("price_per_unit_min", e.target.value)}
              placeholder="any"
              className={`${inputClass} w-28`}
            />
          </label>
          <label className="flex flex-col gap-1 text-xs text-dim">
            $/unit max
            <input
              type="number"
              value={filters.price_per_unit_max}
              onChange={(e) => set("price_per_unit_max", e.target.value)}
              placeholder="any"
              className={`${inputClass} w-28`}
            />
          </label>
        </>
      )}

      {/* Zoning matters most for industrial, but the field exists on every
          comp -- only surface the filter when it's actually useful. */}
      {isIndustrial && (
        <label className="flex flex-col gap-1 text-xs text-dim">
          zoning
          <input
            value={filters.zoning}
            onChange={(e) => set("zoning", e.target.value)}
            placeholder="e.g. M-1"
            className={`${inputClass} w-24`}
          />
        </label>
      )}

      <label className="flex flex-col gap-1 text-xs text-dim">
        from
        <input
          type="date"
          value={filters.date_from}
          onChange={(e) => set("date_from", e.target.value)}
          className={inputClass}
        />
      </label>

      <label className="flex flex-col gap-1 text-xs text-dim">
        to
        <input
          type="date"
          value={filters.date_to}
          onChange={(e) => set("date_to", e.target.value)}
          className={inputClass}
        />
      </label>

      {hasAnyFilter && (
        <button
          onClick={() => onChange(EMPTY_FILTERS)}
          className="px-2 py-1.5 text-xs text-dim hover:text-foreground"
        >
          clear
        </button>
      )}
    </div>
  );
}
