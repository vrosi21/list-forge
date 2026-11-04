import type { Finding, GeneratedCopy, ProductFacts, Provenance, Status } from "@/lib/api";

export interface OutcomeExample {
  readonly status: Status;
  readonly facts: ProductFacts;
  readonly output: GeneratedCopy;
  readonly findings: readonly Finding[];
  readonly provenance: Provenance;
}

export const APPROVED_EXAMPLE: OutcomeExample = {
  status: "approved",
  facts: {
    sku: "MS-RQZ-102",
    name: "Rose Quartz Crystal Sphere 35 mm",
    product_type: "sphere",
    stones: ["rose quartz"],
    colours: ["pink"],
    materials: [],
    size_mm: "35",
    weight_g: null,
    pieces: 1,
    origin: null,
    price_eur: null,
  },
  output: {
    title: "Rose Quartz Crystal Sphere 35 mm",
    short_description: "A pink rose quartz sphere, 35 mm, perfect for an altar or bedside ritual",
    description:
      "You hold a rose quartz sphere, its surface a soft pink glow. The sphere measures 35 mm across, round and smooth. It feels light in your hand. Place it on an altar, on a desk, or keep it beside your bed. It sits as a quiet companion in your daily ritual, a gentle presence that invites calm. The stone’s color is a gentle pink that reflects your own gentle intention. The sphere’s single piece is ready to be used in your practice. You feel its presence in the moment, grounding your intention without promise of outcome.",
    bullets: [
      "Rose quartz, soft pink",
      "Sphere, 35 mm",
      "Single piece",
      "Ideal for altar or bedside",
      "Calm, grounding presence",
    ],
    seo_title: "Rose Quartz Sphere 35 mm – Mindful Souls",
    meta_description:
      "Rose quartz sphere, 35 mm, soft pink, single piece. Ideal for altar or bedside. Calm and grounding.",
  },
  findings: [],
  provenance: {
    brand_id: "mindful-souls",
    prompt_version: "copy-v1",
    prompt_fingerprint: "1cc0c551a47c",
    params: {
      model: "openai/gpt-oss-20b",
      temperature: 0.7,
      reasoning_effort: "low",
      max_completion_tokens: 1500,
    },
    usage: { prompt_tokens: 468, cached_prompt_tokens: 0, completion_tokens: 285 },
    attempts: 1,
    cost_usd: "0.000121",
    cache_hit: false,
    created_at: "2026-11-04T13:51:41.083898Z",
  },
};

export const NEEDS_REVIEW_EXAMPLE: OutcomeExample = {
  status: "needs_review",
  facts: {
    sku: "MS-SEL-104",
    name: "Selenite Crystal Wand Cleansing Healing Tool",
    product_type: "wand",
    stones: ["selenite"],
    colours: ["white"],
    materials: [],
    size_mm: "200",
    weight_g: "150",
    pieces: 1,
    origin: "Morocco",
    price_eur: null,
  },
  output: {
    title: "Selenite Crystal Wand 200mm",
    short_description: "200mm white selenite crystal wand, 150g, single piece",
    description:
      "This white selenite crystal wand measures 200mm in length and weighs 150 grams. It is a single piece, making it easy to handle and incorporate into your jewelry or ritual practices. The wand is sourced from Morocco, adding a unique provenance to its clear, smooth surface. Its neutral white hue allows it to blend seamlessly with other components or stand out as a focal point. Ideal for cleansing, healing, or decorative purposes, this wand offers a straightforward, practical tool for makers and practitioners alike.",
    bullets: ["200mm length", "150g weight", "Single piece", "White selenite", "Origin Morocco"],
    seo_title: "Selenite Crystal Wand 200mm",
    meta_description:
      "White selenite crystal wand, 200mm long, 150g, single piece, from Morocco. Ideal for cleansing and healing.",
  },
  findings: [
    {
      check: "entity",
      field: "description",
      start: 250,
      end: 255,
      text: "clear",
      message: "clear is not one of this product's attributes",
      severity: "warn",
    },
    {
      check: "claim",
      field: "description",
      start: 399,
      end: 406,
      text: "healing",
      message: "'healing' is a claim this brand does not make",
      severity: "block",
    },
    {
      check: "claim",
      field: "meta_description",
      start: 99,
      end: 106,
      text: "healing",
      message: "'healing' is a claim this brand does not make",
      severity: "block",
    },
  ],
  provenance: {
    brand_id: "beads-and-stones",
    prompt_version: "copy-v1",
    prompt_fingerprint: "b48caa21c9bc",
    params: {
      model: "openai/gpt-oss-20b",
      temperature: 0.7,
      reasoning_effort: "low",
      max_completion_tokens: 1500,
    },
    usage: { prompt_tokens: 1085, cached_prompt_tokens: 0, completion_tokens: 375 },
    attempts: 2,
    cost_usd: "0.000194",
    cache_hit: false,
    created_at: "2026-09-21T05:27:57.239979Z",
  },
};
