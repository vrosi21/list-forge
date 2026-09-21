import { describe, expect, it } from "vitest";
import { formatFact, formatFieldName, formatInteger, formatUsd } from "@/lib/format";

describe("formatUsd", () => {
  it.each([
    { value: "0.0123456", expected: "$0.0123" },
    { value: "0", expected: "$0.0000" },
    { value: "1.5", expected: "$1.5000" },
    { value: null, expected: "n/a" },
    { value: undefined, expected: "n/a" },
    { value: "not a number", expected: "n/a" },
  ])("formats $value", ({ value, expected }) => {
    expect(formatUsd(value)).toBe(expected);
  });
});

describe("formatFact", () => {
  it.each([
    { value: ["amethyst", "quartz"], expected: "amethyst, quartz" },
    { value: [], expected: "n/a" },
    { value: "brazil", expected: "brazil" },
    { value: "", expected: "n/a" },
    { value: null, expected: "n/a" },
    { value: 40, expected: "40" },
  ])("formats $value", ({ value, expected }) => {
    expect(formatFact(value)).toBe(expected);
  });
});

describe("formatFieldName", () => {
  it.each([
    { field: "short_description", expected: "Short description" },
    { field: "bullets[0]", expected: "Bullet 1" },
    { field: "bullets[2]", expected: "Bullet 3" },
    { field: "needs_review", expected: "Needs review" },
  ])("names $field", ({ field, expected }) => {
    expect(formatFieldName(field)).toBe(expected);
  });
});

describe("formatInteger", () => {
  it("groups thousands", () => {
    expect(formatInteger(12345)).toBe("12,345");
  });
});
