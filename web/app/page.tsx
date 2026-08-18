"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth";
import Cursor from "@/components/Cursor";

export default function LandingPage() {
  const { email, loading } = useAuth();

  return (
    <div className="mx-auto flex max-w-3xl flex-col items-center px-6 py-24 text-center">
      <p className="text-sm text-dim">$ forward-a-flyer --get comps</p>
      <h1 className="mt-3 text-3xl font-medium tracking-tight sm:text-4xl">
        Forward your flyers.
        <br />
        Get instant comps.
        <Cursor className="ml-2" />
      </h1>
      <p className="mt-6 max-w-xl text-base text-dim">
        Deal Archive reads every sale and lease flyer that lands in your
        inbox and turns it into a searchable, personal comp database &mdash;
        built from deal flow you already see.
      </p>

      <div className="mt-10 flex gap-4">
        {!loading && email ? (
          <Link
            href="/sale"
            className="border border-accent px-6 py-3 font-medium text-accent hover:bg-accent hover:text-background"
          >
            go_to_vault
          </Link>
        ) : (
          <>
            <Link
              href="/sign-up"
              className="border border-accent bg-accent px-6 py-3 font-medium text-background hover:bg-transparent hover:text-accent"
            >
              get_started
            </Link>
            <Link
              href="/sign-in"
              className="border border-line px-6 py-3 font-medium text-foreground hover:border-dim"
            >
              sign_in
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
      <div className="flex h-8 w-8 items-center justify-center border border-accent text-sm font-medium text-accent">
        {n}
      </div>
      <h3 className="mt-3 font-medium">{title}</h3>
      <p className="mt-1 text-sm text-dim">{body}</p>
    </div>
  );
}
