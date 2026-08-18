"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";
import Cursor from "./Cursor";

const LINKS = [
  { href: "/sale", label: "sale" },
  { href: "/lease", label: "lease" },
  { href: "/upload", label: "upload" },
  { href: "/settings", label: "settings" },
];

export default function Nav() {
  const { email, loading, signOut } = useAuth();
  const pathname = usePathname();

  return (
    <header className="border-b border-line">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-center gap-2 font-medium tracking-tight">
          <span className="text-dim">~/</span>deal-archive
          <Cursor />
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
              sign_out
            </button>
          </nav>
        )}

        {!loading && !email && (
          <nav className="flex items-center gap-4 text-sm">
            <Link href="/sign-in" className="text-dim hover:text-foreground">
              sign_in
            </Link>
            <Link
              href="/sign-up"
              className="border border-accent px-3 py-1.5 font-medium text-accent hover:bg-accent hover:text-background"
            >
              sign_up
            </Link>
          </nav>
        )}
      </div>
    </header>
  );
}
