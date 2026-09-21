import Link from "next/link";
import { OPERATOR, REPOSITORY_URL, SITE_NAME } from "@/lib/site";

export function SiteFooter() {
  return (
    <footer className="mt-24 border-t border-rule">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-4 px-6 py-8 text-sm text-muted sm:flex-row sm:items-start sm:justify-between">
        <p className="max-w-xl">
          {SITE_NAME} is a portfolio project by {OPERATOR.name}. It is not affiliated with,
          authorised or endorsed by Foxelli Group or any brand named on this site.
        </p>
        <nav className="flex flex-wrap gap-x-5 gap-y-2">
          <Link href="/privacy" className="hover:text-ink">
            Privacy
          </Link>
          <Link href="/terms" className="hover:text-ink">
            Terms
          </Link>
          <Link href="/legal" className="hover:text-ink">
            Legal notice
          </Link>
          <a href={REPOSITORY_URL} className="hover:text-ink">
            Source
          </a>
        </nav>
      </div>
    </footer>
  );
}
