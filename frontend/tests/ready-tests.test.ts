import { readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { DEFAULT_MAX_ROWS, missingRequired, toCsv } from "@/lib/catalogue";
import { READY_TESTS, readyTestFile } from "@/lib/ready-tests";

const BRANDS_DIR = join(__dirname, "..", "..", "backend", "brands");
const BRAND_IDS = readdirSync(BRANDS_DIR)
  .filter((name) => name.endsWith(".toml") && name !== "vocab.toml")
  .map((name) => name.replace(/\.toml$/, ""));

describe("READY_TESTS", () => {
  it("has unique ids", () => {
    const ids = READY_TESTS.map((test) => test.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it.each(READY_TESTS)("$id uses a brand the backend ships", (test) => {
    expect(BRAND_IDS).toContain(test.brandId);
  });

  it.each(READY_TESTS)("$id fits the default row limit", (test) => {
    expect(test.rows.length).toBeGreaterThan(0);
    expect(test.rows.length).toBeLessThanOrEqual(DEFAULT_MAX_ROWS);
  });

  it.each(READY_TESTS)("$id has a SKU and a name on every row", (test) => {
    expect(missingRequired(test.rows)).toEqual([]);
  });

  it("has no SKU in more than one test", () => {
    const skus = READY_TESTS.flatMap((test) => test.rows.map((product) => product.sku));
    expect(new Set(skus).size).toBe(skus.length);
  });
});

describe("readyTestFile", () => {
  it("wraps the rows as a CSV file named after the test", async () => {
    const test = READY_TESTS[0];
    const file = readyTestFile(test);
    expect(file.name).toBe(`${test.id}.csv`);
    expect(file.type).toBe("text/csv");
    expect(await file.text()).toBe(toCsv(test.rows));
  });
});
