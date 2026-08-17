"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth";

export default function LandingPage() {
  const { email, loading } = useAuth();

  return (
    <div className="mx-auto flex max-w-3xl flex-col items-center px-6 py-24 text-center">
      <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
        Forward your flyers.
        <br />
        Get instant comps.
      </h1>
      <p className="mt-6 max-w-xl text-lg text-black/60 dark:text-white/60">
        Deal Archive reads every sale and lease flyer that lands in your
        inbox and turns it into a searchable, personal comp database &mdash;
        built from deal flow you already see.
      </p>

      <div className="mt-10 flex gap-4">
        {!loading && email ? (
          <Link
            href="/sale"
            className="rounded-md bg-orange-600 px-6 py-3 font-medium text-white hover:bg-orange-700"
          >
            Go to your vault
          </Link>
        ) : (
          <>
            <Link
              href="/sign-up"
              className="rounded-md bg-orange-600 px-6 py-3 font-medium text-white hover:bg-orange-700"
            >
              Get started
            </Link>
            <Link
              href="/sign-in"
              className="rounded-md border border-black/15 px-6 py-3 font-medium hover:bg-black/5 dark:border-white/20 dark:hover:bg-white/10"
            >
              Sign in
            </Link>
          </>
        )}
      </div>

      <div className="mt-20 grid grid-cols-1 gap-8 text-left sm:grid-cols-3">
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
    <div>
      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-orange-600/10 text-sm font-semibold text-orange-600 dark:text-orange-400">
        {n}
      </div>
      <h3 className="mt-3 font-medium">{title}</h3>
      <p className="mt-1 text-sm text-black/60 dark:text-white/60">{body}</p>
    </div>
  );
}
