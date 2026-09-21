"use client";

import type { Item } from "@/lib/api";
import { findingsOf } from "@/lib/batch";
import { CopyFields } from "@/components/CopyFields";
import { FactsTable } from "@/components/FactsTable";
import { FindingList } from "@/components/FindingList";
import { ProvenanceFooter } from "@/components/ProvenanceFooter";
import { StatusBadge } from "@/components/StatusBadge";

interface ReviewPanelProps {
  item: Item | null;
  regenerating: boolean;
  onRegenerate: (itemId: string) => void;
}

export function ReviewPanel({ item, regenerating, onRegenerate }: ReviewPanelProps) {
  if (item === null) {
    return (
      <section className="rounded-lg border border-rule bg-surface p-6 text-sm text-muted">
        Select a row to see the product facts beside the generated copy.
      </section>
    );
  }

  const findings = findingsOf(item);

  return (
    <section className="flex flex-col gap-5 rounded-lg border border-rule bg-surface p-5">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-col gap-1">
          <h2 className="text-lg font-semibold text-ink">{item.facts.name}</h2>
          <div className="flex items-center gap-2 text-xs text-muted">
            <span className="font-mono">{item.facts.sku}</span>
            <StatusBadge status={item.status} />
          </div>
        </div>
        <button
          type="button"
          onClick={() => onRegenerate(item.id)}
          disabled={regenerating}
          className="rounded border border-accent px-3 py-1.5 text-sm font-semibold text-accent disabled:opacity-40"
        >
          {regenerating ? "Regenerating" : "Regenerate"}
        </button>
      </header>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.6fr)]">
        <div className="flex flex-col gap-2">
          <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted">
            Product facts
          </h3>
          <FactsTable facts={item.facts} />
        </div>

        <div className="flex flex-col gap-2">
          <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted">
            Generated copy
          </h3>
          {item.output ? (
            <CopyFields copy={item.output} findings={findings} />
          ) : (
            <p className="text-sm text-muted">No valid output was produced.</p>
          )}
        </div>
      </div>

      {item.error ? (
        <div className="flex flex-col gap-2 rounded border border-bad/40 bg-bad-soft p-3">
          <h3 className="text-[11px] font-semibold uppercase tracking-wide text-bad">Failure</h3>
          <p className="text-sm text-ink">{item.error}</p>
          {item.raw_output ? (
            <pre className="max-h-64 overflow-auto rounded bg-surface p-3 font-mono text-xs text-ink-soft whitespace-pre-wrap">
              {item.raw_output}
            </pre>
          ) : null}
        </div>
      ) : null}

      <div className="flex flex-col gap-2">
        <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted">Findings</h3>
        <FindingList findings={findings} />
      </div>

      {item.provenance ? <ProvenanceFooter provenance={item.provenance} /> : null}
    </section>
  );
}
