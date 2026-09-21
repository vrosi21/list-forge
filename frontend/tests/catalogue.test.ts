import { describe, expect, it } from "vitest";
import {
  COLUMNS,
  SAMPLE_ROWS,
  filledRows,
  missingRequired,
  row,
  toCsv,
  withCell,
  withEmptyRow,
  withoutRow,
} from "@/lib/catalogue";

const HEADER =
  "sku,name,product_type,stones,colours,materials,size_mm,weight_g,pieces,origin,price_eur";

describe("toCsv", () => {
  it("writes the header the backend expects", () => {
    expect(toCsv([]).split("\n")[0]).toBe(HEADER);
  });

  it.each([
    { name: "plain", value: "amethyst", expected: "amethyst" },
    { name: "comma", value: "a, b", expected: '"a, b"' },
    { name: "quote", value: 'the "best"', expected: '"the ""best"""' },
    { name: "newline", value: "a\nb", expected: '"a\nb"' },
    { name: "apostrophe", value: "tiger's eye", expected: "tiger's eye" },
    { name: "semicolon list", value: "purple; white", expected: "purple; white" },
    { name: "padding", value: "  pink  ", expected: "pink" },
  ])("quotes a $name value correctly", ({ value, expected }) => {
    const line = toCsv([row({ sku: "X", name: value })]).split("\n").slice(1).join("\n");

    expect(line.startsWith(`X,${expected},`)).toBe(true);
  });

  it("writes one line per row and a trailing newline", () => {
    const csv = toCsv(SAMPLE_ROWS);

    expect(csv.endsWith("\n")).toBe(true);
    expect(csv.trimEnd().split("\n")).toHaveLength(SAMPLE_ROWS.length + 1);
  });

  it("keeps every column for an empty row", () => {
    expect(toCsv([row()]).split("\n")[1]).toBe(",".repeat(COLUMNS.length - 1));
  });
});

describe("row editing", () => {
  it("changes one cell and leaves the others alone", () => {
    const rows = withCell(SAMPLE_ROWS, 1, "origin", "Brazil");

    expect(rows[1].origin).toBe("Brazil");
    expect(rows[1].sku).toBe(SAMPLE_ROWS[1].sku);
    expect(rows[0]).toBe(SAMPLE_ROWS[0]);
  });

  it("removes the row at an index", () => {
    const rows = withoutRow(SAMPLE_ROWS, 0);

    expect(rows.map((current) => current.sku)).toEqual(
      SAMPLE_ROWS.slice(1).map((current) => current.sku),
    );
  });

  it.each([
    { name: "below the cap", start: 2, max: 5, expected: 3 },
    { name: "at the cap", start: 5, max: 5, expected: 5 },
    { name: "over the cap", start: 5, max: 3, expected: 5 },
  ])("adds an empty row only $name", ({ start, max, expected }) => {
    expect(withEmptyRow(SAMPLE_ROWS.slice(0, start), max)).toHaveLength(expected);
  });
});

describe("filledRows", () => {
  it("drops rows with nothing typed in them", () => {
    expect(filledRows([row(), row({ sku: "A" }), row({ origin: " " })])).toHaveLength(1);
  });
});

describe("missingRequired", () => {
  it.each([
    { name: "complete", rows: [row({ sku: "A", name: "N" })], expected: [] },
    { name: "no sku", rows: [row({ name: "N" })], expected: [0] },
    { name: "no name", rows: [row({ sku: "A" })], expected: [0] },
    { name: "blank name", rows: [row({ sku: "A", name: "  " })], expected: [0] },
    {
      name: "second row only",
      rows: [row({ sku: "A", name: "N" }), row({ sku: "B" })],
      expected: [1],
    },
  ])("reports $name", ({ rows, expected }) => {
    expect(missingRequired(rows)).toEqual(expected);
  });

  it("finds nothing missing in the sample", () => {
    expect(missingRequired(SAMPLE_ROWS)).toEqual([]);
  });
});
