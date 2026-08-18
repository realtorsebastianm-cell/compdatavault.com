"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth";
import Cursor from "@/components/Cursor";

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
      <h1 className="flex items-center text-xl font-medium">
        settings
        <Cursor className="ml-2" />
      </h1>

      <div className="mt-8">
        <p className="text-xs uppercase tracking-wide text-dim">Account</p>
        <p className="mt-1">{email}</p>
      </div>

      <div className="mt-8">
        <p className="text-xs uppercase tracking-wide text-dim">
          Your forwarding address
        </p>
        <p className="mt-1 text-sm text-dim">
          Forward any sale or lease flyer to this address and it&rsquo;ll show
          up in your vault automatically.
        </p>
        <div className="mt-3 flex items-center gap-3">
          <code className="border border-line bg-accent/5 px-3 py-2 text-sm text-accent">
            {forwardingAddress ?? "—"}
          </code>
          <button
            onClick={copy}
            className="border border-line px-3 py-2 text-sm text-dim hover:border-dim hover:text-foreground"
          >
            {copied ? "copied" : "copy"}
          </button>
        </div>
      </div>
    </div>
  );
}
