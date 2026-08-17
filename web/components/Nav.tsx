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
    <header className="border-b border-black/10 dark:border-white/10">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="font-semibold tracking-tight">
          Deal Archive
        </Link>

        {!loading && email && (
          <nav className="flex items-center gap-6 text-sm">
            {LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={
                  pathname === link.href
                    ? "font-medium text-orange-600 dark:text-orange-400"
                    : "text-black/60 hover:text-black dark:text-white/60 dark:hover:text-white"
                }
              >
                {link.label}
              </Link>
            ))}
            <button
              onClick={signOut}
              className="text-black/60 hover:text-black dark:text-white/60 dark:hover:text-white"
            >
              Sign out
            </button>
          </nav>
        )}

        {!loading && !email && (
          <nav className="flex items-center gap-4 text-sm">
            <Link href="/sign-in" className="text-black/60 hover:text-black dark:text-white/60 dark:hover:text-white">
              Sign in
            </Link>
            <Link
              href="/sign-up"
              className="rounded-md bg-orange-600 px-3 py-1.5 font-medium text-white hover:bg-orange-700"
            >
              Sign up
            </Link>
          </nav>
        )}
      </div>
    </header>
  );
}
