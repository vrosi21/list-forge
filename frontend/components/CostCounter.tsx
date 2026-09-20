import type { BatchTotals } from "@/lib/api";
import { formatInteger, formatUsd } from "@/lib/format";

function Figure({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[11px] font-semibold uppercase tracking-wide text-muted">{label}</span>
      <span className={`font-mono text-sm ${tone ?? "text-ink"}`}>{value}</span>
    </div>
  );
}

export function CostCounter({ totals }: { totals: BatchTotals }) {
  return (
    <div className="rounded-lg border border-rule bg-surface p-4">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <Figure label="Prompt tokens" value={formatInteger(totals.prompt_tokens)} />
        <Figure label="Provider-cached" value={formatInteger(totals.cached_prompt_tokens)} />
        <Figure label="Completion tokens" value={formatInteger(totals.completion_tokens)} />
        <Figure label="Spent" value={formatUsd(totals.cost_usd)} />
        <Figure label="Saved by cache" value={formatUsd(totals.saved_usd)} tone="text-ok" />
        <Figure label="Cache hits" value={formatInteger(totals.cache_hits)} tone="text-ok" />
      </div>
      <p className="mt-3 text-xs text-muted">
        List-price equivalent: the free plan bills nothing for these calls.
      </p>
    </div>
  );
}
