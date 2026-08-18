"use client";

import { PROPERTY_TYPES, type PropertyType } from "@/lib/api";

export interface VaultFilterState {
  q: string;
  submarket: string;
  property_type: PropertyType | "";
  date_from: string;
  date_to: string;
}

export const EMPTY_FILTERS: VaultFilterState = {
  q: "",
  submarket: "",
  property_type: "",
  date_from: "",
  date_to: "",
};

export function toParams(filters: VaultFilterState): Record<string, string> {
  const params: Record<string, string> = {};
  if (filters.q) params.q = filters.q;
  if (filters.submarket) params.submarket = filters.submarket;
  if (filters.property_type) params.property_type = filters.property_type;
  if (filters.date_from) params.date_from = filters.date_from;
  if (filters.date_to) params.date_to = filters.date_to;
  return params;
}

export default function VaultFilters({
  filters,
  onChange,
}: {
  filters: VaultFilterState;
  onChange: (next: VaultFilterState) => void;
}) {
  function set<K extends keyof VaultFilterState>(key: K, value: VaultFilterState[K]) {
    onChange({ ...filters, [key]: value });
  }

  const inputClass =
    "border border-line bg-transparent px-2 py-1.5 text-sm text-foreground focus:border-accent focus:outline-none";

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

      <label className="flex flex-col gap-1 text-xs text-dim">
        submarket
        <input
          value={filters.submarket}
          onChange={(e) => set("submarket", e.target.value)}
          placeholder="any"
          className={inputClass}
        />
      </label>

      <label className="flex flex-col gap-1 text-xs text-dim">
        property_type
        <select
          value={filters.property_type}
          onChange={(e) =>
            set("property_type", e.target.value as PropertyType | "")
          }
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

      {(filters.q ||
        filters.submarket ||
        filters.property_type ||
        filters.date_from ||
        filters.date_to) && (
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
