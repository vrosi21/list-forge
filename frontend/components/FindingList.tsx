import type { Finding } from "@/lib/api";
import { formatFieldName } from "@/lib/format";

const TONES = {
  block: "border-bad text-bad",
  warn: "border-warn text-warn",
} as const;

export function FindingList({ findings }: { findings: readonly Finding[] }) {
  if (findings.length === 0) {
    return <p className="text-sm text-muted">No findings. A person still decides to publish.</p>;
  }

  return (
    <ul className="flex flex-col gap-2">
      {findings.map((finding, index) => (
        <li
          key={`${finding.field}-${finding.start}-${index}`}
          className={`border-l-2 pl-3 text-sm ${TONES[finding.severity]}`}
        >
          <span className="font-semibold uppercase tracking-wide text-[11px]">
            {finding.severity} · {finding.check}
          </span>
          <p className="text-ink">{finding.message}</p>
          <p className="text-xs text-muted">
            {formatFieldName(finding.field)} · <span className="font-mono">{finding.text}</span>
          </p>
        </li>
      ))}
    </ul>
  );
}
