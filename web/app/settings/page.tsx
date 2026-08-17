"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth";

export default function SettingsPage() {
  const { email, forwardingAddress } = useAuth();
  const [copied, setCopied] = useState(false);

  function copy() {
    if (!forwardingAddress) return;
    navigator.clipboard.writeText(forwardingAddress);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <div className="mx-auto max-w-xl px-6 py-12">
      <h1 className="text-2xl font-semibold">Settings</h1>

      <div className="mt-8">
        <p className="text-xs uppercase tracking-wide text-black/50 dark:text-white/50">
          Account
        </p>
        <p className="mt-1">{email}</p>
      </div>

      <div className="mt-8">
        <p className="text-xs uppercase tracking-wide text-black/50 dark:text-white/50">
          Your forwarding address
        </p>
        <p className="mt-1 text-sm text-black/60 dark:text-white/60">
          Forward any sale or lease flyer to this address and it&rsquo;ll show
          up in your vault automatically.
        </p>
        <div className="mt-3 flex items-center gap-3">
          <code className="rounded-md border border-black/10 bg-black/[0.03] px-3 py-2 text-sm dark:border-white/10 dark:bg-white/[0.05]">
            {forwardingAddress ?? "—"}
          </code>
          <button
            onClick={copy}
            className="rounded-md border border-black/15 px-3 py-2 text-sm hover:bg-black/5 dark:border-white/20 dark:hover:bg-white/10"
          >
            {copied ? "Copied" : "Copy"}
          </button>
        </div>
      </div>
    </div>
  );
}
