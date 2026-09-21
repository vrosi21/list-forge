import type { ReactNode } from "react";
import { LEGAL_UPDATED, OPERATOR, REPOSITORY_URL } from "@/lib/site";

export function LegalPage({ title, children }: { title: string; children: ReactNode }) {
  return (
    <main className="mx-auto w-full max-w-3xl px-6 py-16">
      <h1 className="text-3xl font-semibold tracking-tight text-ink">{title}</h1>
      <p className="mt-2 text-sm text-muted">Last updated {LEGAL_UPDATED}</p>
      <div className="legal mt-8">{children}</div>
    </main>
  );
}

export function Contact() {
  if (OPERATOR.email) {
    return (
      <a href={`mailto:${OPERATOR.email}`} className="underline">
        {OPERATOR.email}
      </a>
    );
  }
  return (
    <>
      an issue on the project&apos;s{" "}
      <a href={`${REPOSITORY_URL}/issues`} className="underline">
        GitHub repository
      </a>
    </>
  );
}
