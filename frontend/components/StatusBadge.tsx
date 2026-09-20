import type { Status } from "@/lib/api";
import { formatStatus } from "@/lib/format";

const TONES: Record<Status, string> = {
  pending: "bg-sunken text-muted",
  processing: "bg-accent-soft text-accent",
  approved: "bg-ok-soft text-ok",
  needs_review: "bg-warn-soft text-warn",
  failed: "bg-bad-soft text-bad",
};

export function StatusBadge({ status }: { status: Status }) {
  return (
    <span
      className={`inline-block rounded px-2 py-0.5 text-xs font-semibold ${TONES[status]}`}
    >
      {formatStatus(status)}
    </span>
  );
}
