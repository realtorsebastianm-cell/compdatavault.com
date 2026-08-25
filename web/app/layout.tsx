import type { Metadata } from "next";
import { IBM_Plex_Mono, Lora } from "next/font/google";
import "./globals.css";
import Link from "next/link";
import { AuthProvider } from "@/lib/auth";
import Nav from "@/components/Nav";

const plexMono = IBM_Plex_Mono({
  variable: "--font-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

const lora = Lora({
  variable: "--font-lora",
  subsets: ["latin"],
  weight: ["500", "600", "700"],
});

export const metadata: Metadata = {
  title: "CompDataVault",
  description: "Forward your flyers, get instant comps.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${plexMono.variable} ${lora.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">
        <AuthProvider>
          <Nav />
          <main className="flex-1">{children}</main>
          <footer className="border-t border-line py-6 text-center text-xs text-dim">
            <Link href="/terms" className="hover:text-foreground">
              Terms_of_Service
            </Link>
            <span className="mx-2">&middot;</span>
            <Link href="/privacy" className="hover:text-foreground">
              Privacy_Policy
            </Link>
          </footer>
        </AuthProvider>
      </body>
    </html>
  );
}
