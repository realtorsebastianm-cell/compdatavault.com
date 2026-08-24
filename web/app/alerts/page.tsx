"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import {
  api,
  type DealType,
  type SavedSearch,
  type SavedSearchMatch,
} from "@/lib/api";
import Cursor from "@/components/Cursor";

export default function AlertsPage() {
  const [searches, setSearches] = useState<SavedSearch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [query, setQuery] = useState("");
  const [creating, setCreating] = useState(false);

  const [expanded, setExpanded] = useState<string | null>(null);
  const [matches, setMatches] = useState<Record<string, SavedSearchMatch[]>>({});
  const [matchesLoading, setMatchesLoading] = useState(false);

  function reload() {
    setLoading(true);
    api
      .savedSearches()
      .then(setSearches)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load"))
      .finally(() => setLoading(false));
  }

  useEffect(reload, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!name.trim() || !query.trim() || creating) return;
    setCreating(true);
    setError(null);
    try {
      const search = await api.createSavedSearch(name.trim(), query.trim());
      setSearches((prev) => [search, ...prev]);
      setName("");
      setQuery("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't save that search");
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(id: string) {
    try {
      await api.deleteSavedSearch(id);
      setSearches((prev) => prev.filter((s) => s.id !== id));
      if (expanded === id) setExpanded(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't delete that search");
    }
  }

  async function toggleExpand(id: string) {
    if (expanded === id) {
      setExpanded(null);
      return;
    }
    setExpanded(id);
    if (!matches[id]) {
      setMatchesLoading(true);
      try {
        const result = await api.savedSearchMatches(id);
        setMatches((prev) => ({ ...prev, [id]: result }));
        // Viewing matches marks them seen server-side -- reflect that in
        // the unseen badge immediately rather than waiting on a reload.
        setSearches((prev) =>
          prev.map((s) => (s.id === id ? { ...s, unseen_count: 0 } : s))
        );
      } catch (err) {
        setError(err instanceof Error ? err.message : "Couldn't load matches");
      } finally {
        setMatchesLoading(false);
      }
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <h1 className="flex items-center text-xl font-medium">
        alerts
        <Cursor className="ml-2" />
      </h1>
      <p className="mt-2 text-sm text-dim">
        Save an Ask AI-style query and get flagged here the moment a new
        upload or forwarded flyer matches it -- no need to remember to
        re-run the search yourself.
      </p>

      <form onSubmit={handleCreate} className="mt-6 flex flex-col gap-2">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder='Name, e.g. "Northgate industrial under $10M"'
          className="border border-line bg-transparent px-3 py-2 text-sm text-foreground focus:border-accent focus:outline-none"
        />
        <div className="flex gap-2">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Same kind of query you'd type into Ask AI"
            className="flex-1 border border-line bg-transparent px-3 py-2 text-sm text-foreground focus:border-accent focus:outline-none"
          />
          <button
            type="submit"
            disabled={creating || !name.trim() || !query.trim()}
            className="border border-accent bg-accent px-4 py-2 text-sm font-medium text-background hover:bg-transparent hover:text-accent disabled:cursor-not-allowed disabled:opacity-50"
          >
            {creating ? "saving..." : "save_search"}
          </button>
        </div>
      </form>

      {error && <p className="mt-4 text-sm text-red-400">{error}</p>}

      {!loading && searches.length === 0 && (
        <p className="mt-8 text-sm text-dim">
          No saved searches yet. Save one above and it&rsquo;ll start
          watching every new comp that comes into your vault.
        </p>
      )}

      <div className="mt-6 flex flex-col gap-3">
        {searches.map((s) => (
          <div key={s.id} className="border border-line">
            <div className="flex items-center justify-between p-4">
              <button
                onClick={() => toggleExpand(s.id)}
                className="flex-1 text-left"
              >
                <div className="flex items-center gap-2">
                  <p className="font-medium">{s.name}</p>
                  {s.unseen_count > 0 && (
                    <span className="rounded-full bg-accent px-1.5 py-0.5 text-[10px] font-medium leading-none text-background">
                      {s.unseen_count} new
                    </span>
                  )}
                </div>
                <p className="mt-1 text-xs text-dim">{s.query}</p>
              </button>
              <button
                onClick={() => handleDelete(s.id)}
                className="ml-4 text-xs text-dim hover:text-red-400"
              >
                remove
              </button>
            </div>

            {expanded === s.id && (
              <div className="border-t border-line p-4">
                {matchesLoading && !matches[s.id] ? (
                  <p className="flex items-center text-sm text-dim">
                    loading
                    <Cursor className="ml-2" />
                  </p>
                ) : matches[s.id] && matches[s.id].length === 0 ? (
                  <p className="text-sm text-dim">
                    No matches yet -- this is checked against every new
                    comp as it comes in.
                  </p>
                ) : (
                  <div className="flex flex-col gap-2">
                    {matches[s.id]?.map((m) => (
                      <MatchRow key={m.id} match={m} />
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function MatchRow({ match }: { match: SavedSearchMatch }) {
  const { comp, deal_type } = match;
  const href = `/comps?type=${deal_type}&id=${comp.id}`;
  return (
    <Link
      href={href}
      className="block border border-line p-3 text-sm hover:border-accent"
    >
      <div className="flex items-center justify-between">
        <p className="font-medium">{comp.address}</p>
        <span className="text-xs uppercase tracking-wide text-dim">
          {deal_type as DealType}
        </span>
      </div>
      <p className="mt-1 text-dim">
        {comp.submarket ?? "—"} &middot;{" "}
        <span className="capitalize">{comp.property_type}</span>
        {comp.building_sf ? ` · ${comp.building_sf.toLocaleString()} SF` : ""}
      </p>
    </Link>
  );
}
