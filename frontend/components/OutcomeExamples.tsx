import type { Brand } from "@/lib/api";
import { rowFromFacts, summariseRow } from "@/lib/catalogue";
import { APPROVED_EXAMPLE, NEEDS_REVIEW_EXAMPLE, type OutcomeExample } from "@/lib/examples";
import { segmentField } from "@/lib/highlight";
import { CopyFields, MarkedText } from "@/components/CopyFields";
import { FindingList } from "@/components/FindingList";
import { ProvenanceFooter } from "@/components/ProvenanceFooter";
import { StatusBadge } from "@/components/StatusBadge";

const LABEL = "text-[11px] font-semibold uppercase tracking-wide text-muted";

function brandName(brands: readonly Brand[], brandId: string): string {
  return brands.find((brand) => brand.id === brandId)?.name ?? brandId;
}

interface ExampleCardProps {
  example: OutcomeExample;
  caption: string;
  brands: readonly Brand[];
}

function ExampleCard({ example, caption, brands }: ExampleCardProps) {
  const descriptionFindings = example.findings.filter(
    (finding) => finding.field === "description",
  );

  return (
    <article className="flex flex-col gap-4 rounded-lg border border-rule bg-surface p-5">
      <header className="flex flex-col gap-2">
        <span className="self-start">
          <StatusBadge status={example.status} />
        </span>
        <p className="text-sm text-ink-soft">{caption}</p>
      </header>

      <div className="flex flex-col gap-1">
        <h3 className="font-medium text-ink">{example.facts.name}</h3>
        <p className="text-xs text-muted">
          <span className="font-mono">{example.facts.sku}</span> ·{" "}
          {brandName(brands, example.provenance.brand_id)}
        </p>
      </div>

      <div className="flex flex-col gap-1">
        <h4 className={LABEL}>Product row</h4>
        <p className="font-mono text-xs text-ink-soft">
          {summariseRow(rowFromFacts(example.facts))}
        </p>
      </div>

      <div className="flex flex-col gap-1">
        <h4 className={LABEL}>Description</h4>
        <p className="text-sm leading-relaxed text-ink">
          <MarkedText segments={segmentField(example.output.description, descriptionFindings)} />
        </p>
      </div>

      <div className="flex flex-col gap-2">
        <h4 className={LABEL}>Findings</h4>
        <FindingList findings={example.findings} />
      </div>

      <details className="group mt-auto border-t border-rule pt-3">
        <summary className="cursor-pointer list-none text-sm text-ink-soft hover:text-ink">
          <span className="group-open:hidden">Show every field and the run details</span>
          <span className="hidden group-open:inline">Hide the details</span>
        </summary>
        <div className="mt-4 flex flex-col gap-4">
          <CopyFields copy={example.output} findings={example.findings} />
          <ProvenanceFooter provenance={example.provenance} />
        </div>
      </details>
    </article>
  );
}

function FailedCard() {
  return (
    <article className="flex flex-col gap-4 rounded-lg border border-dashed border-rule-strong bg-surface p-5">
      <header className="flex flex-col gap-2">
        <span className="self-start">
          <StatusBadge status="failed" />
        </span>
        <p className="text-sm text-ink-soft">
          No usable draft came back, even after the model was shown its errors and asked again.
        </p>
      </header>
      <p className="text-sm text-ink-soft">
        This happens when every reply is malformed JSON or misses a required field, or when
        the provider keeps refusing the request. The item keeps the last reply and the reason,
        and Regenerate tries again.
      </p>
      <p className="text-sm text-ink-soft">
        It is the rarest outcome, so there is no sample here. Failed items show up under their
        own tab in the results.
      </p>
    </article>
  );
}

export function OutcomeExamples({ brands }: { brands: readonly Brand[] }) {
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <ExampleCard
        example={APPROVED_EXAMPLE}
        caption="The checks found nothing the row does not support. It still waits for a person to publish it."
        brands={brands}
      />
      <ExampleCard
        example={NEEDS_REVIEW_EXAMPLE}
        caption="The checks found words the row does not support. Each one is marked where it appears."
        brands={brands}
      />
      <FailedCard />
    </div>
  );
}
