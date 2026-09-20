import type { BatchResponse, Finding, Item, Status } from "@/lib/api";

export const TAB_STATUSES = ["needs_review", "approved", "failed"] as const;

export type TabStatus = (typeof TAB_STATUSES)[number];

const UNFINISHED: Status[] = ["pending", "processing"];

export interface Progress {
  readonly done: number;
  readonly total: number;
  readonly running: boolean;
}

export function progressOf(counts: BatchResponse["counts"]): Progress {
  const total = Object.values(counts).reduce((sum, count) => sum + count, 0);
  const unfinished = UNFINISHED.reduce((sum, status) => sum + (counts[status] ?? 0), 0);
  return { done: total - unfinished, total, running: unfinished > 0 };
}

export function countFor(counts: BatchResponse["counts"], status: TabStatus): number {
  return counts[status] ?? 0;
}

export function itemsFor(items: readonly Item[], status: TabStatus): Item[] {
  return items.filter((item) => item.status === status);
}

export function findingsOf(item: Item): Finding[] {
  return item.findings ?? [];
}

export function firstPopulatedTab(counts: BatchResponse["counts"]): TabStatus {
  return TAB_STATUSES.find((status) => countFor(counts, status) > 0) ?? TAB_STATUSES[0];
}
