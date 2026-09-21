import Link from "next/link";
import { ThemeToggle } from "@/components/ThemeToggle";
import { SITE_NAME } from "@/lib/site";

const LINKS = [
  { href: "/#how", label: "How it works" },
  { href: "/#brands", label: "Brands" },
  { href: "/tool", label: "Tool" },
] as const;

export function SiteHeader() {
  return (
    <header className="border-b border-rule">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-4 px-6 py-4">
        <Link href="/" className="font-mono text-sm font-medium tracking-tight text-ink">
          {SITE_NAME}
        </Link>
        <nav className="flex items-center gap-5 text-sm">
          {LINKS.map((link) => (
            <Link key={link.href} href={link.href} className="text-ink-soft hover:text-ink">
              {link.label}
            </Link>
          ))}
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}
