"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";

const LINKS = [
  { href: "/sale", label: "Sale" },
  { href: "/lease", label: "Lease" },
  { href: "/upload", label: "Upload" },
  { href: "/settings", label: "Settings" },
];

export default function Nav() {
  const { email, loading, signOut } = useAuth();
  const pathname = usePathname();

  return (
    <header className="border-b border-line bg-surface">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link
          href="/"
          className="flex items-center gap-2 font-serif text-lg font-bold tracking-tight"
        >
          Comp<span className="text-accent">Data</span>Vault
        </Link>

        {!loading && email && (
          <nav className="flex items-center gap-6 text-sm">
            {LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={
                  pathname === link.href
                    ? "text-accent"
                    : "text-dim hover:text-foreground"
                }
              >
                {link.label}
              </Link>
            ))}
            <button onClick={signOut} className="text-dim hover:text-foreground">
              Sign_out
            </button>
          </nav>
        )}

        {!loading && !email && (
          <nav className="flex items-center gap-4 text-sm">
            <Link href="/sign-in" className="text-dim hover:text-foreground">
              Sign_in
            </Link>
            <Link
              href="/sign-up"
              className="rounded-md bg-accent px-4 py-2 font-medium text-background shadow-sm hover:opacity-90"
            >
              Sign_up
            </Link>
          </nav>
        )}
      </div>
    </header>
  );
}
