import type { Finding, GeneratedCopy } from "@/lib/api";
import { flattenCopy } from "@/lib/copy";
import { formatFieldName } from "@/lib/format";
import { groupByField, segmentField, type Segment } from "@/lib/highlight";

const MARKS = {
  block: "bg-bad-soft text-bad underline decoration-bad decoration-2",
  warn: "bg-warn-soft text-warn underline decoration-warn decoration-dotted decoration-2",
} as const;

function tooltip(findings: readonly Finding[]): string {
  return findings.map((finding) => `${finding.check}: ${finding.message}`).join("\n");
}

function Marked({ segments }: { segments: readonly Segment[] }) {
  return (
    <>
      {segments.map((segment, index) =>
        segment.severity === null ? (
          <span key={index}>{segment.text}</span>
        ) : (
          <mark
            key={index}
            title={tooltip(segment.findings)}
            className={`rounded-sm px-0.5 ${MARKS[segment.severity]}`}
          >
            {segment.text}
          </mark>
        ),
      )}
    </>
  );
}

interface CopyFieldsProps {
  copy: GeneratedCopy;
  findings: readonly Finding[];
}

export function CopyFields({ copy, findings }: CopyFieldsProps) {
  const byField = groupByField(findings);

  return (
    <dl className="flex flex-col gap-4">
      {flattenCopy(copy).map(([field, text]) => (
        <div key={field} className="flex flex-col gap-1">
          <dt className="text-[11px] font-semibold uppercase tracking-wide text-muted">
            {formatFieldName(field)}
          </dt>
          <dd className="text-sm leading-relaxed text-ink">
            <Marked segments={segmentField(text, byField.get(field) ?? [])} />
          </dd>
        </div>
      ))}
    </dl>
  );
}
