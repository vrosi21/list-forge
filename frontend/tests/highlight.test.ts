import { describe, expect, it } from "vitest";
import type { Finding } from "@/lib/api";
import { groupByField, segmentField } from "@/lib/highlight";

function finding(start: number, end: number, overrides: Partial<Finding> = {}): Finding {
  return {
    check: "entity",
    field: "description",
    start,
    end,
    text: "",
    message: "not supported by the facts",
    severity: "warn",
    ...overrides,
  };
}

function shape(text: string, findings: Finding[]) {
  return segmentField(text, findings).map((segment) => [segment.text, segment.severity]);
}

describe("segmentField", () => {
  it.each([
    {
      name: "no findings leaves one plain segment",
      text: "amethyst point",
      findings: [],
      expected: [["amethyst point", null]],
    },
    {
      name: "empty text produces no segments",
      text: "",
      findings: [],
      expected: [],
    },
    {
      name: "one finding splits the text in three",
      text: "made of labradorite here",
      findings: [finding(8, 19)],
      expected: [
        ["made of ", null],
        ["labradorite", "warn"],
        [" here", null],
      ],
    },
    {
      name: "a finding at the start leaves no leading segment",
      text: "labradorite bead",
      findings: [finding(0, 11)],
      expected: [
        ["labradorite", "warn"],
        [" bead", null],
      ],
    },
    {
      name: "adjacent findings stay separate",
      text: "heals cancer",
      findings: [finding(0, 5, { severity: "block" }), finding(6, 12)],
      expected: [
        ["heals", "block"],
        [" ", null],
        ["cancer", "warn"],
      ],
    },
    {
      name: "the stronger severity wins inside an overlap",
      text: "heals 99 percent",
      findings: [finding(0, 8, { severity: "block" }), finding(6, 8, { check: "number" })],
      expected: [
        ["heals ", "block"],
        ["99", "block"],
        [" percent", null],
      ],
    },
    {
      name: "a warn span outside a block span keeps its own tone",
      text: "purple heals fast",
      findings: [finding(0, 6), finding(7, 12, { severity: "block" })],
      expected: [
        ["purple", "warn"],
        [" ", null],
        ["heals", "block"],
        [" fast", null],
      ],
    },
    {
      name: "a span past the end is clamped",
      text: "brazil",
      findings: [finding(0, 99, { check: "origin" })],
      expected: [["brazil", "warn"]],
    },
    {
      name: "an empty span is dropped",
      text: "brazil",
      findings: [finding(3, 3)],
      expected: [["brazil", null]],
    },
    {
      name: "a reversed span is dropped",
      text: "brazil",
      findings: [finding(5, 2)],
      expected: [["brazil", null]],
    },
    {
      name: "identical spans are reported once",
      text: "labradorite",
      findings: [finding(0, 11), finding(0, 11, { check: "claim" })],
      expected: [["labradorite", "warn"]],
    },
  ])("$name", ({ text, findings, expected }) => {
    expect(shape(text, findings)).toEqual(expected);
  });

  it("keeps every finding that covers a segment", () => {
    const covering = [finding(0, 8, { severity: "block" }), finding(6, 8, { check: "number" })];

    const segments = segmentField("heals 99 percent", covering);

    expect(segments[1].findings).toHaveLength(2);
  });

  it("rebuilds the original text", () => {
    const text = "Amethyst heals, and it weighs 40 grams.";
    const findings = [finding(9, 14, { severity: "block" }), finding(30, 32, { check: "number" })];

    const rebuilt = segmentField(text, findings)
      .map((segment) => segment.text)
      .join("");

    expect(rebuilt).toBe(text);
  });
});

describe("groupByField", () => {
  it("keeps findings in their original order per field", () => {
    const findings = [
      finding(0, 1, { field: "title" }),
      finding(2, 3, { field: "description" }),
      finding(4, 5, { field: "title" }),
    ];

    const grouped = groupByField(findings);

    expect([...grouped.keys()]).toEqual(["title", "description"]);
    expect(grouped.get("title")?.map((item) => item.start)).toEqual([0, 4]);
  });
});
