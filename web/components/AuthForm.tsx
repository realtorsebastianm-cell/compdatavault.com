"use client";

import { useState, type FormEvent } from "react";
import { useAuth } from "@/lib/auth";
import Cursor from "./Cursor";

export default function AuthForm({ mode }: { mode: "sign-in" | "sign-up" }) {
  const { signIn, signUp } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (mode === "sign-in") {
        await signIn(email, password);
      } else {
        await signUp(email, password);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={onSubmit}
      className="mx-auto mt-16 flex max-w-sm flex-col gap-4 px-6"
    >
      <h1 className="flex items-center text-xl font-medium">
        {mode === "sign-in" ? "sign_in" : "create_account"}
        <Cursor className="ml-2" />
      </h1>

      <label className="flex flex-col gap-1 text-sm text-dim">
        email
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="border border-line bg-transparent px-3 py-2 text-foreground focus:border-accent focus:outline-none"
        />
      </label>

      <label className="flex flex-col gap-1 text-sm text-dim">
        password
        <input
          type="password"
          required
          minLength={8}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="border border-line bg-transparent px-3 py-2 text-foreground focus:border-accent focus:outline-none"
        />
      </label>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <button
        type="submit"
        disabled={submitting}
        className="mt-2 border border-accent bg-accent px-4 py-2 font-medium text-background hover:bg-transparent hover:text-accent disabled:opacity-50"
      >
        {submitting ? "..." : mode === "sign-in" ? "sign_in" : "sign_up"}
      </button>
    </form>
  );
}
