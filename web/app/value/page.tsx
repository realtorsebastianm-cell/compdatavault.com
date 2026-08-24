"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { api, type DealType, type ValueMatch, type ValueResponse } from "@/lib/api";
import Cursor from "@/components/Cursor";

const RATE_LABEL: Record<string, string> = {
  per_sf_year: "/SF/yr",
  per_sf_month: "/SF/mo",
  flat_month: "/mo",
};

const EXAMPLE =
  "22,000 SF industrial building on a 1.1 acre lot in the Northgate submarket, built 2014, 20' clear height, 2 dock doors and 1 drive-in, M-1 zoned, recently re-roofed.";

export default function ValuePage() {
  const [description, setDescription] = useState("");
  const [dealType, setDealType] = useState<DealType>("sale");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<ValueResponse | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!description.trim() || loading) return;
    setLoading(true);
    setError(null);
    try {
      const result = await api.value(description, dealType);
      setResponse(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Valuation failed");
      setResponse(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <h1 className="flex items-center text-xl font-medium">
        value_my_property
        <Cursor className="ml-2" />
      </h1>
      <p className="mt-2 text-sm text-dim">
        Describe the property you&rsquo;re valuing -- size, submarket,
        zoning, condition, whatever you&rsquo;d put on a flyer -- and
        we&rsquo;ll match it against your own vault and estimate a value
        off the closest comps.
      </p>

      <form onSubmit={onSubmit} className="mt-6 flex flex-col gap-3">
        <div className="flex gap-2 text-xs">
          {(["sale", "lease"] as const).map((dt) => (
            <button
              key={dt}
              type="button"
              onClick={() => setDealType(dt)}
              className={`border px-3 py-1.5 font-medium uppercase tracking-wide ${
                dealType === dt
                  ? "border-accent bg-accent text-background"
                  : "border-line text-dim hover:border-accent hover:text-foreground"
              }`}
            >
              {dt}
            </button>
          ))}
        </div>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder={EXAMPLE}
          rows={5}
          className="border border-line bg-transparent px-3 py-2 text-sm text-foreground focus:border-accent focus:outline-none"
        />
        <button
          type="submit"
          disabled={loading || !description.trim()}
          className="self-start border border-accent bg-accent px-4 py-2 text-sm font-medium text-background hover:bg-transparent hover:text-accent disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "matching..." : "find_comps"}
        </button>
      </form>

      {error && <p className="mt-6 text-sm text-red-400">{error}</p>}

      {response && !loading && (
        <div className="mt-8">
          <UnderstoodSummary understood={response.understood} narrowedBy={response.narrowed_by} />

          {response.estimate && (
            <div className="mt-4 border border-accent/40 bg-accent/[0.05] px-4 py-3 text-sm">
              <p className="text-xs uppercase tracking-wide text-dim">
                Rough estimate, based on {response.estimate.based_on} comp
                {response.estimate.based_on === 1 ? "" : "s"}
              </p>
              <p className="mt-1 text-lg font-medium">
                ${response.estimate.average.toFixed(2)}
                <span className="text-sm text-dim">
                  {" "}
                  {response.estimate.metric === "price_per_sf"
                    ? "/SF"
                    : response.estimate.rate_type
                      ? RATE_LABEL[response.estimate.rate_type] ?? ""
                      : ""}
                </span>
              </p>
              <p className="text-xs text-dim">
                Range: ${response.estimate.low.toFixed(2)} &ndash; $
                {response.estimate.high.toFixed(2)}
              </p>
              {response.estimate.metric === "rate" && (
                <p className="mt-1 text-xs text-dim">
                  Averaged only across comps quoted{" "}
                  {response.estimate.rate_type
                    ? RATE_LABEL[response.estimate.rate_type] ?? "the same way"
                    : "the same way"}{" "}
                  -- comps quoted a different way are still shown below but
                  weren&rsquo;t mixed into this number.
                </p>
              )}
              <p className="mt-2 text-xs text-dim">
                This is arithmetic over your matched comps, not a formal
                appraisal -- sanity-check it against the comps below.
              </p>
            </div>
          )}

          {response.matches.length === 0 ? (
            <p className="mt-6 text-sm text-dim">
              No comps in your vault are close enough to this yet.
            </p>
          ) : (
            <div className="mt-6 flex flex-col gap-3">
              {response.matches.map((m) => (
                <MatchCard key={m.comp.id} match={m} dealType={dealType} />
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
  narrowedBy,
}: {
  understood: Record<string, unknown>;
  narrowedBy: string[];
}) {
  const entries = Object.entries(understood);
  if (entries.length === 0) return null;

  return (
    <div className="border border-line bg-accent/[0.03] px-4 py-3 text-xs text-dim">
      <span className="uppercase tracking-wide">understood as</span>{" "}
      {entries.map(([k, v]) => (
        <span key={k} className="mr-3">
          <span className="text-foreground">{k}</span>={String(v)}
        </span>
      ))}
      {narrowedBy.length === 0 && entries.length > 0 && (
        <p className="mt-1">
          Couldn&rsquo;t narrow by any of those fields with enough comps in
          your vault -- showing your broader vault instead.
        </p>
      )}
    </div>
  );
}

function MatchCard({ match, dealType }: { match: ValueMatch; dealType: DealType }) {
  const { comp, reason } = match;
  const href = `/comps?type=${dealType}&id=${comp.id}`;

  return (
    <Link
      href={href}
      className="block border border-line p-4 text-sm hover:border-accent"
    >
      <div className="flex items-center justify-between">
        <p className="font-medium">{comp.address}</p>
        <span className="text-xs uppercase tracking-wide text-dim">
          {comp.submarket ?? "—"}
        </span>
      </div>
      <p className="mt-1 text-dim">
        <span className="capitalize">{comp.property_type}</span>
        {comp.building_sf ? ` · ${comp.building_sf.toLocaleString()} SF` : ""}
      </p>
      {reason && <p className="mt-2 text-accent">{reason}</p>}
    </Link>
  );
}
