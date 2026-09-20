"use client";

import type { BatchResponse } from "@/lib/api";
import { TAB_STATUSES, countFor, type TabStatus } from "@/lib/batch";
import { formatStatus } from "@/lib/format";

interface StatusTabsProps {
  counts: BatchResponse["counts"];
  active: TabStatus;
  onSelect: (status: TabStatus) => void;
}

export function StatusTabs({ counts, active, onSelect }: StatusTabsProps) {
  return (
    <div role="tablist" className="flex gap-1 border-b border-rule">
      {TAB_STATUSES.map((status) => {
        const selected = status === active;
        return (
          <button
            key={status}
            type="button"
            role="tab"
            aria-selected={selected}
            onClick={() => onSelect(status)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium ${
              selected
                ? "border-accent text-ink"
                : "border-transparent text-muted hover:text-ink-soft"
            }`}
          >
            {formatStatus(status)}
            <span className="ml-2 font-mono text-xs text-muted">{countFor(counts, status)}</span>
          </button>
        );
      })}
    </div>
  );
}
