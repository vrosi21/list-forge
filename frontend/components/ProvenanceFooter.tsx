import type { Provenance } from "@/lib/api";
import { formatTimestamp, formatUsd } from "@/lib/format";

function Entry({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col">
      <dt className="text-[11px] font-semibold uppercase tracking-wide text-muted">{label}</dt>
      <dd className="font-mono text-xs text-ink-soft">{value}</dd>
    </div>
  );
}

export function ProvenanceFooter({ provenance }: { provenance: Provenance }) {
  return (
    <dl className="grid grid-cols-2 gap-3 border-t border-rule pt-3 sm:grid-cols-4">
      <Entry label="Prompt" value={`${provenance.prompt_version} · ${provenance.prompt_fingerprint}`} />
      <Entry label="Model" value={provenance.params.model} />
      <Entry
        label="Sampling"
        value={`t=${provenance.params.temperature} · ${provenance.params.reasoning_effort ?? "default"}`}
      />
      <Entry label="Attempts" value={String(provenance.attempts)} />
      <Entry label="Cost" value={formatUsd(provenance.cost_usd)} />
      <Entry label="Result cache" value={provenance.cache_hit ? "hit" : "miss"} />
      <Entry label="Brand" value={provenance.brand_id} />
      <Entry label="Generated" value={formatTimestamp(provenance.created_at)} />
    </dl>
  );
}
