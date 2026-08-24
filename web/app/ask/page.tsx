"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { api, type AskMatch, type AskResponse } from "@/lib/api";
import Cursor from "@/components/Cursor";

const EXAMPLES = [
  "40k SF industrial with 10-18 ft clear height",
  "multifamily under $150k per unit in The Row on Jackson",
  "lease comps zoned M-1 under $0.75/SF/yr",
];

export default function AskPage() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<AskResponse | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!query.trim() || loading) return;
    setLoading(true);
    setError(null);
    try {
      const result = await api.ask(query);
      setResponse(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
      setResponse(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <h1 className="flex items-center text-xl font-medium">
        ask_ai
        <Cursor className="ml-2" />
      </h1>
      <p className="mt-2 text-sm text-dim">
        Describe what you&rsquo;re looking for in plain language and
        we&rsquo;ll search your vault for it -- size, price, zoning, and
        anything else that showed up in a flyer&rsquo;s notes.
      </p>

      <form onSubmit={onSubmit} className="mt-6 flex gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. 40k SF industrial with 10-18 ft clear height"
          className="flex-1 border border-line bg-transparent px-3 py-2 text-sm text-foreground focus:border-accent focus:outline-none"
        />
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="border border-accent bg-accent px-4 py-2 text-sm font-medium text-background hover:bg-transparent hover:text-accent disabled:cursor-not-allowed disabled:opacity-50"
        >
          search
        </button>
      </form>

      {!response && !loading && (
        <div className="mt-4 flex flex-wrap gap-2">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              onClick={() => setQuery(ex)}
              className="border border-line px-2 py-1 text-xs text-dim hover:border-accent hover:text-foreground"
            >
              {ex}
            </button>
          ))}
        </div>
      )}

      {loading && (
        <p className="mt-6 flex items-center text-sm text-dim">
          searching
          <Cursor className="ml-2" />
        </p>
      )}

      {error && <p className="mt-6 text-sm text-red-400">{error}</p>}

      {response && !loading && (
        <div className="mt-8">
          <UnderstoodSummary
            understood={response.understood}
            residual={response.residual_criteria}
          />

          {response.matches.length === 0 ? (
            <p className="mt-6 text-sm text-dim">
              No comps in your vault match that yet.
            </p>
          ) : (
            <div className="mt-6 flex flex-col gap-3">
              {response.matches.map((m) => (
                <MatchCard key={`${m.deal_type}-${m.comp.id}`} match={m} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function UnderstoodSummary({
  understood,
  residual,
}: {
  understood: Record<string, unknown>;
  residual: string | null;
}) {
  const entries = Object.entries(understood);
  if (entries.length === 0 && !residual) return null;

  return (
    <div className="border border-line bg-accent/[0.03] px-4 py-3 text-xs text-dim">
      <span className="uppercase tracking-wide">understood as</span>{" "}
      {entries.map(([k, v]) => (
        <span key={k} className="mr-3">
          <span className="text-foreground">{k}</span>={String(v)}
        </span>
      ))}
      {residual && (
        <span>
          <span className="text-foreground">also matching notes for</span>{" "}
          &ldquo;{residual}&rdquo;
        </span>
      )}
    </div>
  );
}

function MatchCard({ match }: { match: AskMatch }) {
  const { comp, deal_type, reason } = match;
  const href = `/comps?type=${deal_type}&id=${comp.id}`;

  return (
    <Link
      href={href}
      className="block border border-line p-4 text-sm hover:border-accent"
    >
      <div className="flex items-center justify-between">
        <p className="font-medium">{comp.address}</p>
        <span className="text-xs uppercase tracking-wide text-dim">
          {deal_type}
        </span>
      </div>
      <p className="mt-1 text-dim">
        {comp.submarket ?? "—"} &middot;{" "}
        <span className="capitalize">{comp.property_type}</span>
        {comp.building_sf ? ` · ${comp.building_sf.toLocaleString()} SF` : ""}
      </p>
      {reason && <p className="mt-2 text-accent">{reason}</p>}
    </Link>
  );
}
