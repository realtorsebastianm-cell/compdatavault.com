"use client";

import { useCallback, useState, type DragEvent } from "react";
import Link from "next/link";
import { api, type FlyerResult } from "@/lib/api";
import Cursor from "@/components/Cursor";

export default function UploadPage() {
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<FlyerResult[]>([]);

  const handleFiles = useCallback(async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    setError(null);
    try {
      for (const file of Array.from(files)) {
        const result = await api.uploadFlyer(file);
        setResults((prev) => [result, ...prev]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }, []);

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragOver(false);
    handleFiles(e.dataTransfer.files);
  }

  return (
    <div className="mx-auto max-w-2xl px-6 py-12">
      <h1 className="flex items-center text-xl font-medium">
        upload_flyer
        <Cursor className="ml-2" />
      </h1>
      <p className="mt-2 text-sm text-dim">
        Drop a sale or lease flyer (PDF or image). We&rsquo;ll detect which
        one it is and file it into the right vault.
      </p>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        className={`mt-6 flex flex-col items-center justify-center border-2 border-dashed px-6 py-16 text-center transition-colors ${
          dragOver ? "border-accent bg-accent/5" : "border-line"
        }`}
      >
        <p className="text-sm text-dim">Drag and drop a flyer here, or</p>
        <label className="mt-3 cursor-pointer border border-accent bg-accent px-4 py-2 text-sm font-medium text-background hover:bg-transparent hover:text-accent">
          choose_file
          <input
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,.webp"
            multiple
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
        </label>
        {uploading && (
          <p className="mt-4 flex items-center text-sm text-dim">
            extracting
            <Cursor className="ml-2" />
          </p>
        )}
      </div>

      {error && <p className="mt-4 text-sm text-red-400">{error}</p>}

      {results.length > 0 && (
        <div className="mt-8 flex flex-col gap-4">
          {results.map((r) => (
            <ResultCard key={r.flyer_id} result={r} />
          ))}
        </div>
      )}
    </div>
  );
}

function ResultCard({ result }: { result: FlyerResult }) {
  if (result.status === "failed") {
    return (
      <div className="border border-red-900 bg-red-950/30 p-4 text-sm">
        <p className="font-medium text-red-400">extraction_failed</p>
        <p className="mt-1 text-red-400/70">{result.error}</p>
      </div>
    );
  }

  const href =
    result.deal_type && result.comp_id
      ? `/comps?type=${result.deal_type}&id=${result.comp_id}`
      : undefined;

  return (
    <div className="border border-line p-4 text-sm">
      <div className="flex items-center justify-between">
        <p className="font-medium capitalize">
          {result.deal_type ?? "unknown"} flyer parsed
        </p>
        {href && (
          <Link href={href} className="text-accent hover:underline">
            view_comp &rarr;
          </Link>
        )}
      </div>

      {result.low_confidence_fields.length > 0 && (
        <p className="mt-2 text-amber-400">
          Double-check: {result.low_confidence_fields.join(", ")}
        </p>
      )}

      {result.comparison && (
        <p className="mt-2 text-dim">
          This is{" "}
          <span className="font-medium text-foreground">
            {result.comparison.pct_diff > 0 ? "+" : ""}
            {result.comparison.pct_diff}%
          </span>{" "}
          vs. your last {result.comparison.comp_count} comp
          {result.comparison.comp_count === 1 ? "" : "s"} in that submarket
          (avg {result.comparison.baseline_avg.toLocaleString()}).
        </p>
      )}

      {result.possible_duplicate && (
        <p className="mt-2 text-amber-400">
          Possible duplicate of{" "}
          <Link
            href={`/comps?type=${result.deal_type}&id=${result.possible_duplicate.comp_id}`}
            className="underline hover:text-amber-300"
          >
            {result.possible_duplicate.address}
          </Link>{" "}
          already in your vault.
        </p>
      )}

      {result.matched_saved_searches.length > 0 && (
        <p className="mt-2 text-accent">
          Matches your saved search
          {result.matched_saved_searches.length === 1 ? "" : "es"}:{" "}
          {result.matched_saved_searches.join(", ")} --{" "}
          <Link href="/alerts" className="underline">
            view in Alerts
          </Link>
          .
        </p>
      )}
    </div>
  );
}
