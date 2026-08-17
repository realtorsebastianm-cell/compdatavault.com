"use client";

import { useCallback, useState, type DragEvent } from "react";
import Link from "next/link";
import { api, type FlyerResult } from "@/lib/api";

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
      <h1 className="text-2xl font-semibold">Upload a flyer</h1>
      <p className="mt-2 text-sm text-black/60 dark:text-white/60">
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
        className={`mt-6 flex flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-16 text-center transition-colors ${
          dragOver
            ? "border-orange-500 bg-orange-500/5"
            : "border-black/15 dark:border-white/20"
        }`}
      >
        <p className="text-sm text-black/60 dark:text-white/60">
          Drag and drop a flyer here, or
        </p>
        <label className="mt-3 cursor-pointer rounded-md bg-orange-600 px-4 py-2 text-sm font-medium text-white hover:bg-orange-700">
          Choose file
          <input
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,.webp"
            multiple
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
        </label>
        {uploading && (
          <p className="mt-4 text-sm text-black/60 dark:text-white/60">
            Extracting&hellip;
          </p>
        )}
      </div>

      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}

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
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm dark:border-red-900 dark:bg-red-950/30">
        <p className="font-medium text-red-700 dark:text-red-400">
          Extraction failed
        </p>
        <p className="mt-1 text-red-600/80 dark:text-red-400/70">
          {result.error}
        </p>
      </div>
    );
  }

  const href =
    result.deal_type && result.comp_id
      ? `/comps?type=${result.deal_type}&id=${result.comp_id}`
      : undefined;

  return (
    <div className="rounded-lg border border-black/10 p-4 text-sm dark:border-white/10">
      <div className="flex items-center justify-between">
        <p className="font-medium capitalize">
          {result.deal_type ?? "unknown"} flyer parsed
        </p>
        {href && (
          <Link href={href} className="text-orange-600 hover:underline dark:text-orange-400">
            View comp &rarr;
          </Link>
        )}
      </div>

      {result.low_confidence_fields.length > 0 && (
        <p className="mt-2 text-amber-600 dark:text-amber-400">
          Double-check: {result.low_confidence_fields.join(", ")}
        </p>
      )}

      {result.comparison && (
        <p className="mt-2 text-black/70 dark:text-white/70">
          This is{" "}
          <span className="font-medium">
            {result.comparison.pct_diff > 0 ? "+" : ""}
            {result.comparison.pct_diff}%
          </span>{" "}
          vs. your last {result.comparison.comp_count} comp
          {result.comparison.comp_count === 1 ? "" : "s"} in that submarket
          (avg {result.comparison.baseline_avg.toLocaleString()}).
        </p>
      )}
    </div>
  );
}
