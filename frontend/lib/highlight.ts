import type { components } from "@/lib/api-types";

type Finding = components["schemas"]["Finding"];
type Severity = components["schemas"]["Severity"];

export interface Segment {
  readonly text: string;
  readonly severity: Severity | null;
  readonly findings: readonly Finding[];
}

interface Span {
  readonly start: number;
  readonly end: number;
  readonly finding: Finding;
}

export function segmentField(text: string, findings: readonly Finding[]): Segment[] {
  const spans = clampSpans(text, findings);
  if (spans.length === 0) {
    return text.length > 0 ? [{ text, severity: null, findings: [] }] : [];
  }

  const segments: Segment[] = [];
  for (const [start, end] of boundaryPairs(text, spans)) {
    const covering = spans.filter((span) => span.start <= start && span.end >= end);
    segments.push({
      text: text.slice(start, end),
      severity: strongestSeverity(covering),
      findings: covering.map((span) => span.finding),
    });
  }
  return merge(segments);
}

function clampSpans(text: string, findings: readonly Finding[]): Span[] {
  return findings
    .map((finding) => ({
      start: Math.max(0, Math.min(finding.start, text.length)),
      end: Math.max(0, Math.min(finding.end, text.length)),
      finding,
    }))
    .filter((span) => span.start < span.end)
    .sort((first, second) => first.start - second.start || first.end - second.end);
}

function boundaryPairs(text: string, spans: readonly Span[]): Array<[number, number]> {
  const boundaries = new Set<number>([0, text.length]);
  for (const span of spans) {
    boundaries.add(span.start);
    boundaries.add(span.end);
  }
  const ordered = [...boundaries].sort((first, second) => first - second);
  return ordered.slice(0, -1).map((start, index) => [start, ordered[index + 1]]);
}

function strongestSeverity(spans: readonly Span[]): Severity | null {
  if (spans.some((span) => span.finding.severity === "block")) {
    return "block";
  }
  return spans.length > 0 ? "warn" : null;
}

function merge(segments: readonly Segment[]): Segment[] {
  const merged: Segment[] = [];
  for (const segment of segments) {
    const previous = merged.at(-1);
    if (previous && previous.severity === segment.severity && sameFindings(previous, segment)) {
      merged[merged.length - 1] = { ...previous, text: previous.text + segment.text };
      continue;
    }
    merged.push(segment);
  }
  return merged;
}

function sameFindings(first: Segment, second: Segment): boolean {
  return (
    first.findings.length === second.findings.length &&
    first.findings.every((finding, index) => finding === second.findings[index])
  );
}

export function groupByField(findings: readonly Finding[]): Map<string, Finding[]> {
  const grouped = new Map<string, Finding[]>();
  for (const finding of findings) {
    const existing = grouped.get(finding.field);
    if (existing) {
      existing.push(finding);
      continue;
    }
    grouped.set(finding.field, [finding]);
  }
  return grouped;
}
