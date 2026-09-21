import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { describe, expect, it } from "vitest";

const ROOT = join(__dirname, "..");
const SCANNED = ["app", "components", "lib"];
const SKIPPED = new Set(["lib/api-types.ts"]);
const EXTENSIONS = /\.(tsx?|css)$/;

const FORBIDDEN_CHARACTERS = [
  { name: "em dash", pattern: /—/ },
  { name: "en dash", pattern: /–/ },
];

const FORBIDDEN_WORDS = [
  "seamless",
  "seamlessly",
  "leverage",
  "elevate",
  "unlock",
  "empower",
  "robust",
  "delve",
  "cutting-edge",
  "game-changer",
  "revolutionize",
  "revolutionise",
  "harness",
  "streamline",
  "effortless",
  "effortlessly",
  "supercharge",
  "unleash",
  "synergy",
  "holistic",
  "tapestry",
  "look no further",
  "deep dive",
  "in today's",
];

function sourceFiles(directory: string): string[] {
  return readdirSync(directory).flatMap((entry) => {
    const path = join(directory, entry);
    if (statSync(path).isDirectory()) {
      return sourceFiles(path);
    }
    return EXTENSIONS.test(entry) ? [path] : [];
  });
}

const FILES = SCANNED.flatMap((directory) => sourceFiles(join(ROOT, directory)))
  .map((path) => ({ path, name: relative(ROOT, path).replace(/\\/g, "/") }))
  .filter((file) => !SKIPPED.has(file.name));

describe("site copy", () => {
  it("scans a meaningful number of files", () => {
    expect(FILES.length).toBeGreaterThan(10);
  });

  it.each(FILES)("$name uses no dashes that read as generated", ({ path }) => {
    const text = readFileSync(path, "utf-8");
    const found = FORBIDDEN_CHARACTERS.filter((character) => character.pattern.test(text));

    expect(found.map((character) => character.name)).toEqual([]);
  });

  it.each(FILES)("$name avoids stock marketing vocabulary", ({ path }) => {
    const text = readFileSync(path, "utf-8").toLowerCase();
    const found = FORBIDDEN_WORDS.filter((word) =>
      new RegExp(`\\b${word.replace(/[-']/g, "[-']")}\\b`).test(text),
    );

    expect(found).toEqual([]);
  });
});
