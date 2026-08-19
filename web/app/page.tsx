"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth";
import Cursor from "@/components/Cursor";

export default function LandingPage() {
  const { email, loading } = useAuth();

  return (
    <div className="mx-auto flex max-w-3xl flex-col items-center px-6 py-24 text-center">
      <p className="text-sm font-semibold uppercase tracking-wide text-accent">
        Your own private comp vault
      </p>
      <h1 className="mt-3 font-serif text-4xl font-bold tracking-tight text-foreground sm:text-5xl">
        Forward your flyers.
        <br />
        Get instant comps.
        <Cursor className="ml-2" />
      </h1>
      <p className="mt-6 max-w-xl text-base text-dim">
        CompDataVault reads every sale and lease flyer that lands in your
        inbox and turns it into a searchable, personal comp database &mdash;
        built from deal flow you already see.
      </p>

      <div className="mt-10 flex gap-4">
        {!loading && email ? (
          <Link
            href="/sale"
            className="rounded-md bg-accent px-6 py-3 font-medium text-background shadow-md hover:opacity-90"
          >
            Go_to_vault
          </Link>
        ) : (
          <>
            <Link
              href="/sign-up"
              className="rounded-md bg-accent px-6 py-3 font-medium text-background shadow-md hover:opacity-90"
            >
              Get_started
            </Link>
            <Link
              href="/sign-in"
              className="rounded-md border border-line bg-surface px-6 py-3 font-medium text-foreground hover:border-dim"
            >
              Sign_in
            </Link>
          </>
        )}
      </div>

      <div className="mt-20 grid grid-cols-1 gap-6 text-left sm:grid-cols-3">
        <Step
          n="1"
          title="Forward or upload"
          body="Send flyers to your unique inbox address, or drop them on the upload page."
        />
        <Step
          n="2"
          title="AI extracts the data"
          body="Address, size, price or rate, cap rate, term, broker &mdash; parsed straight from the PDF."
        />
        <Step
          n="3"
          title="Compare instantly"
          body="See how a new flyer stacks up against your last comps in that submarket."
        />
      </div>
    </div>
  );
}

function Step({ n, title, body }: { n: string; title: string; body: string }) {
  return (
    <div className="rounded-lg border border-line bg-surface p-6">
      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-accent font-serif text-sm font-bold text-background">
        {n}
      </div>
      <h3 className="mt-3 font-serif font-semibold text-foreground">{title}</h3>
      <p className="mt-1 text-sm text-dim">{body}</p>
    </div>
  );
}
