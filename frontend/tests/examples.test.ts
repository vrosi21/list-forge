import { describe, expect, it } from "vitest";
import { flattenCopy } from "@/lib/copy";
import { APPROVED_EXAMPLE, NEEDS_REVIEW_EXAMPLE } from "@/lib/examples";

const EXAMPLES = [APPROVED_EXAMPLE, NEEDS_REVIEW_EXAMPLE];

describe("outcome examples", () => {
  it.each(EXAMPLES)("$status points every finding at its own text", (example) => {
    const fields = new Map(flattenCopy(example.output));
    for (const finding of example.findings) {
      expect(fields.get(finding.field)?.slice(finding.start, finding.end)).toBe(finding.text);
    }
  });

  it("keeps the approved sample free of findings", () => {
    expect(APPROVED_EXAMPLE.findings).toEqual([]);
  });

  it("shows at least one finding of each severity in the review sample", () => {
    const severities = new Set(NEEDS_REVIEW_EXAMPLE.findings.map((finding) => finding.severity));
    expect(severities).toEqual(new Set(["warn", "block"]));
  });

  it.each(EXAMPLES)("$status records a real model call", (example) => {
    expect(example.provenance.cache_hit).toBe(false);
    expect(example.provenance.attempts).toBeGreaterThan(0);
  });
});
