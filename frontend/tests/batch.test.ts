import { describe, expect, it } from "vitest";
import type { Item } from "@/lib/api";
import {
  countFor,
  firstPopulatedTab,
  itemsFor,
  progressOf,
  type Progress,
  type TabStatus,
} from "@/lib/batch";

interface ProgressCase {
  name: string;
  counts: Record<string, number>;
  expected: Progress;
}

interface TabCase {
  counts: Record<string, number>;
  expected: TabStatus;
}

function item(id: string, status: Item["status"]): Item {
  return {
    id,
    batch_id: "batch",
    row_number: 1,
    facts: { sku: `SKU-${id}`, name: "Amethyst point" },
    status,
  };
}

describe("progressOf", () => {
  it.each<ProgressCase>([
    {
      name: "counts unfinished work as running",
      counts: { pending: 2, processing: 1, approved: 3, needs_review: 0, failed: 0 },
      expected: { done: 3, total: 6, running: true },
    },
    {
      name: "is finished when nothing is pending or processing",
      counts: { pending: 0, processing: 0, approved: 4, needs_review: 1, failed: 1 },
      expected: { done: 6, total: 6, running: false },
    },
    {
      name: "handles an empty batch",
      counts: {},
      expected: { done: 0, total: 0, running: false },
    },
  ])("$name", ({ counts, expected }) => {
    expect(progressOf(counts)).toEqual(expected);
  });
});

describe("countFor", () => {
  it("reads zero for a status the API did not send", () => {
    expect(countFor({ approved: 2 }, "failed")).toBe(0);
  });
});

describe("itemsFor", () => {
  it("keeps only the items in that tab", () => {
    const items = [item("a", "approved"), item("b", "failed"), item("c", "approved")];

    expect(itemsFor(items, "approved").map((each) => each.id)).toEqual(["a", "c"]);
  });
});

describe("firstPopulatedTab", () => {
  it.each<TabCase>([
    { counts: { needs_review: 1, approved: 4 }, expected: "needs_review" },
    { counts: { approved: 4 }, expected: "approved" },
    { counts: { failed: 2 }, expected: "failed" },
    { counts: {}, expected: "needs_review" },
  ])("picks $expected", ({ counts, expected }) => {
    expect(firstPopulatedTab(counts)).toBe(expected);
  });
});
