import type { Progress } from "@/lib/batch";
import { formatInteger } from "@/lib/format";

export function ProgressBar({ progress }: { progress: Progress }) {
  const percent = progress.total === 0 ? 0 : Math.round((progress.done / progress.total) * 100);

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-baseline justify-between text-sm">
        <span className="font-medium text-ink-soft">
          {progress.running ? "Generating" : "Finished"}
        </span>
        <span className="font-mono text-muted">
          {formatInteger(progress.done)} / {formatInteger(progress.total)}
        </span>
      </div>
      <div
        className="h-1.5 overflow-hidden rounded bg-rule"
        role="progressbar"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div className="h-full bg-accent transition-[width]" style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}
