import type { GeneratedCopy } from "@/lib/api";

export type CopyField = readonly [field: string, text: string];

export function flattenCopy(copy: GeneratedCopy): CopyField[] {
  return [
    ["title", copy.title],
    ["short_description", copy.short_description],
    ["description", copy.description],
    ...copy.bullets.map((bullet, index): CopyField => [`bullets[${index}]`, bullet]),
    ["seo_title", copy.seo_title],
    ["meta_description", copy.meta_description],
  ];
}
