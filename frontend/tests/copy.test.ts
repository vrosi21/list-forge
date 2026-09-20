import { describe, expect, it } from "vitest";
import type { GeneratedCopy } from "@/lib/api";
import { flattenCopy } from "@/lib/copy";

const COPY: GeneratedCopy = {
  title: "Amethyst Point in Deep Purple",
  short_description: "A single amethyst point, polished for a desk.",
  description: "An amethyst point with purple and white banding.",
  bullets: ["Amethyst point", "Purple banding", "One piece"],
  seo_title: "Amethyst Point, Purple",
  meta_description: "An amethyst point with purple and white banding.",
};

describe("flattenCopy", () => {
  it("uses the field names the checks report", () => {
    expect(flattenCopy(COPY).map(([field]) => field)).toEqual([
      "title",
      "short_description",
      "description",
      "bullets[0]",
      "bullets[1]",
      "bullets[2]",
      "seo_title",
      "meta_description",
    ]);
  });

  it("carries every value", () => {
    expect(flattenCopy(COPY).map(([, text]) => text)).toContain("Purple banding");
  });
});
