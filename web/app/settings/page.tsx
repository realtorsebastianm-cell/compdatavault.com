"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "@/lib/auth";
import { api, type AuthorizedSender } from "@/lib/api";
import Cursor from "@/components/Cursor";

export default function SettingsPage() {
  const { email, forwardingAddress } = useAuth();
  const [copied, setCopied] = useState(false);

  const [senders, setSenders] = useState<AuthorizedSender[]>([]);
  const [sendersLoading, setSendersLoading] = useState(true);
  const [newSenderEmail, setNewSenderEmail] = useState("");
  const [addingSender, setAddingSender] = useState(false);
  const [senderError, setSenderError] = useState<string | null>(null);

  useEffect(() => {
    api
      .senders()
      .then(setSenders)
      .catch(() => {
        /* non-critical -- the section just stays empty */
      })
      .finally(() => setSendersLoading(false));
  }, []);

  async function handleAddSender(e: FormEvent) {
    e.preventDefault();
    if (!newSenderEmail.trim() || addingSender) return;
    setAddingSender(true);
    setSenderError(null);
    try {
      const sender = await api.addSender(newSenderEmail.trim());
      setSenders((prev) => [sender, ...prev.filter((s) => s.id !== sender.id)]);
      setNewSenderEmail("");
    } catch (err) {
      setSenderError(err instanceof Error ? err.message : "Couldn't add that address");
    } finally {
      setAddingSender(false);
    }
  }

  async function handleRemoveSender(id: string) {
    try {
      await api.deleteSender(id);
      setSenders((prev) => prev.filter((s) => s.id !== id));
    } catch (err) {
      setSenderError(err instanceof Error ? err.message : "Couldn't remove that address");
    }
  }

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

      <div className="mt-8">
        <p className="text-xs uppercase tracking-wide text-dim">
          Other inboxes you forward from
        </p>
        <p className="mt-1 text-sm text-dim">
          Only flyers forwarded from {email ?? "your account email"} land in
          your vault by default. Add another address here if you also
          receive flyers on a second inbox.
        </p>

        <form onSubmit={handleAddSender} className="mt-3 flex gap-2">
          <input
            type="email"
            value={newSenderEmail}
            onChange={(e) => setNewSenderEmail(e.target.value)}
            placeholder="you@brokerage.com"
            className="flex-1 border border-line bg-transparent px-3 py-2 text-sm text-foreground focus:border-accent focus:outline-none"
          />
          <button
            type="submit"
            disabled={addingSender || !newSenderEmail.trim()}
            className="border border-accent bg-accent px-4 py-2 text-sm font-medium text-background hover:bg-transparent hover:text-accent disabled:cursor-not-allowed disabled:opacity-50"
          >
            {addingSender ? "adding..." : "add"}
          </button>
        </form>

        {senderError && <p className="mt-2 text-sm text-red-400">{senderError}</p>}

        {!sendersLoading && senders.length > 0 && (
          <div className="mt-4 flex flex-col gap-3">
            {senders.map((s) => (
              <div key={s.id} className="border border-line p-3 text-sm">
                <div className="flex items-center justify-between">
                  <span>{s.email}</span>
                  <div className="flex items-center gap-3">
                    {s.verified ? (
                      <span className="text-xs uppercase tracking-wide text-accent">
                        verified
                      </span>
                    ) : (
                      <span className="text-xs uppercase tracking-wide text-amber-400">
                        pending
                      </span>
                    )}
                    <button
                      onClick={() => handleRemoveSender(s.id)}
                      className="text-xs text-dim hover:text-red-400"
                    >
                      remove
                    </button>
                  </div>
                </div>
                {!s.verified && s.verification_code && (
                  <p className="mt-2 text-xs text-dim">
                    Not verified yet -- send any email from{" "}
                    <span className="text-foreground">{s.email}</span> to{" "}
                    <code className="text-accent">
                      {forwardingAddress ?? "your forwarding address"}
                    </code>{" "}
                    with{" "}
                    <code className="border border-line bg-accent/5 px-1 py-0.5 text-foreground">
                      {s.verification_code}
                    </code>{" "}
                    somewhere in the subject line. Once that arrives,
                    flyers forwarded from this address will file into your
                    vault too.
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
