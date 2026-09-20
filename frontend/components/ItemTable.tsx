"use client";

import type { Item } from "@/lib/api";
import { findingsOf } from "@/lib/batch";

interface ItemTableProps {
  items: readonly Item[];
  selectedId: string | null;
  onSelect: (itemId: string) => void;
}

export function ItemTable({ items, selectedId, onSelect }: ItemTableProps) {
  if (items.length === 0) {
    return <p className="p-4 text-sm text-muted">Nothing in this tab.</p>;
  }

  return (
    <ul className="divide-y divide-rule">
      {items.map((item) => {
        const findings = findingsOf(item);
        const selected = item.id === selectedId;
        return (
          <li key={item.id}>
            <button
              type="button"
              onClick={() => onSelect(item.id)}
              className={`flex w-full items-baseline gap-3 px-4 py-3 text-left text-sm ${
                selected ? "bg-accent-soft" : "hover:bg-sunken"
              }`}
            >
              <span className="w-10 shrink-0 font-mono text-xs text-muted">{item.row_number}</span>
              <span className="w-32 shrink-0 font-mono text-xs text-ink-soft">{item.facts.sku}</span>
              <span className="flex-1 truncate text-ink">{item.facts.name}</span>
              <span className="shrink-0 text-xs text-muted">
                {item.error !== null && item.error !== undefined
                  ? "error"
                  : `${findings.length} finding${findings.length === 1 ? "" : "s"}`}
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
