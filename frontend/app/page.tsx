import Link from "next/link";
import { CodeGate } from "@/components/CodeGate";
import type { Brand } from "@/lib/api";
import { REPOSITORY_URL } from "@/lib/site";

export const revalidate = 3600;

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const STEPS = [
  {
    title: "Products in",
    body: "Upload a CSV, or edit the example table in the tool. One row per product. An empty cell means the fact is unknown.",
  },
  {
    title: "Brand chosen",
    body: "The brand sets the voice and a list of claims that are never allowed. The same product reads differently under each brand.",
  },
  {
    title: "Model drafts",
    body: "One request per product returns a title, a short and a long description, bullet points and SEO fields. A reply in the wrong format is sent back with the errors.",
  },
  {
    title: "Code decides",
    body: "Plain rules compare the draft with the product row. The model never grades its own work.",
  },
] as const;

const OUTCOMES = [
  {
    label: "Approved",
    tone: "bg-ok-soft text-ok",
    body: "No findings. It still waits for a person to publish it.",
  },
  {
    label: "Needs review",
    tone: "bg-warn-soft text-warn",
    body: "At least one finding, marked in the text with the rule that caught it.",
  },
  {
    label: "Failed",
    tone: "bg-bad-soft text-bad",
    body: "No usable draft after retries. The last reply is kept so you can see why.",
  },
] as const;

const CHECKS = [
  {
    title: "Numbers",
    body: "A count, size, weight or price that is not in the row. 24.90 and 24.9 are treated as the same number.",
  },
  {
    title: "Stones, colours, materials",
    body: "Any known term the row does not list, including plurals and spelling variants such as tigers eye.",
  },
  {
    title: "Origin",
    body: "A country or region, or its adjective, that the row does not give.",
  },
  {
    title: "Banned claims",
    body: "Wording the brand forbids, such as heals, cures or relieves anxiety.",
  },
  {
    title: "Missing data",
    body: "Sentences about facts that are absent, such as origin not specified. The model should leave those out.",
  },
] as const;

async function loadBrands(): Promise<Brand[]> {
  try {
    const response = await fetch(`${API_URL}/brands`, { next: { revalidate } });
    return response.ok ? ((await response.json()) as Brand[]) : [];
  } catch {
    return [];
  }
}

function SectionHeading({ id, title, lede }: { id: string; title: string; lede: string }) {
  return (
    <div id={id} className="flex scroll-mt-8 flex-col gap-2">
      <h2 className="text-xl font-semibold tracking-tight text-ink">{title}</h2>
      <p className="max-w-2xl text-ink-soft">{lede}</p>
    </div>
  );
}

export default async function Home() {
  const brands = await loadBrands();

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-24 px-6 py-16">
      <section className="grid items-start gap-10 md:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <div className="flex flex-col gap-5">
          <h1 className="text-4xl font-semibold leading-tight tracking-tight text-ink md:text-5xl">
            Product copy that has to match the catalogue.
          </h1>
          <p className="max-w-xl text-lg text-ink-soft">
            ListForge writes shop listings with a language model, then checks every number,
            stone, colour, material and place against the product&apos;s own data. Anything it
            cannot back up goes to a person, marked where it appears.
          </p>
          <p className="max-w-xl text-ink-soft">Nothing is published on its own.</p>
        </div>
        <CodeGate />
      </section>

      <section className="flex flex-col gap-8">
        <SectionHeading
          id="how"
          title="How it works"
          lede="Each product goes through the same four steps. The model proposes the text; code decides where it goes."
        />
        <ol className="grid gap-px overflow-hidden rounded border border-rule bg-rule md:grid-cols-4">
          {STEPS.map((step, index) => (
            <li key={step.title} className="flex flex-col gap-2 bg-surface p-5">
              <span className="font-mono text-xs text-muted">0{index + 1}</span>
              <h3 className="font-medium text-ink">{step.title}</h3>
              <p className="text-sm text-ink-soft">{step.body}</p>
            </li>
          ))}
        </ol>
        <div className="grid gap-4 md:grid-cols-3">
          {OUTCOMES.map((outcome) => (
            <div key={outcome.label} className="flex flex-col gap-2">
              <span
                className={`self-start rounded px-2 py-0.5 text-xs font-medium ${outcome.tone}`}
              >
                {outcome.label}
              </span>
              <p className="text-sm text-ink-soft">{outcome.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="flex flex-col gap-8">
        <SectionHeading
          id="checks"
          title="What gets flagged"
          lede="The checks look for things that appear in the draft but not in the row. Language models tend to add plausible details nobody supplied, so that is where they look."
        />
        <dl className="grid gap-x-10 gap-y-6 md:grid-cols-2">
          {CHECKS.map((check) => (
            <div key={check.title} className="flex flex-col gap-1 border-t border-rule pt-4">
              <dt className="font-medium text-ink">{check.title}</dt>
              <dd className="text-sm text-ink-soft">{check.body}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="flex flex-col gap-8">
        <SectionHeading
          id="brands"
          title="Brands"
          lede="A brand is a short configuration file. It says who the copy is for, how it should sound and what it must never say. The checks are the same for every brand. Only the prompt and the banned words change."
        />
        {brands.length === 0 ? (
          <p className="text-sm text-muted">Brand details load from the server, which is not answering right now.</p>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {brands.map((brand) => (
              <article key={brand.id} className="flex flex-col gap-4 rounded border border-rule bg-surface p-5">
                <h3 className="font-medium text-ink">{brand.name}</h3>
                <dl className="flex flex-col gap-3 text-sm">
                  <div>
                    <dt className="text-xs text-muted">Writes for</dt>
                    <dd className="text-ink-soft">{brand.audience ?? "Not stated"}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted">Voice</dt>
                    <dd className="text-ink-soft">{brand.voice}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted">Never</dt>
                    <dd>
                      <ul className="flex flex-col gap-1 text-ink-soft">
                        {brand.dont?.map((rule) => <li key={rule}>{rule}</li>)}
                      </ul>
                    </dd>
                  </div>
                </dl>
              </article>
            ))}
          </div>
        )}
        <p className="max-w-2xl text-xs text-muted">
          These voices were inferred from public storefronts. They are not official guidelines,
          and the brands have no involvement with this project.
        </p>
      </section>

      <section className="flex flex-col gap-4 border-t border-rule pt-10">
        <h2 className="text-xl font-semibold tracking-tight text-ink">About this demo</h2>
        <div className="flex max-w-2xl flex-col gap-3 text-ink-soft">
          <p>
            ListForge is a portfolio project. Access is by invitation because each run calls a
            paid model. Each code has a small number of runs per day, and files are limited to a
            few rows.
          </p>
          <p>
            Product rows you upload are stored on the server so results can be shown and reused.
            Please do not upload personal or confidential data. The{" "}
            <Link href="/privacy" className="text-ink underline">
              privacy notice
            </Link>{" "}
            and{" "}
            <Link href="/terms" className="text-ink underline">
              terms
            </Link>{" "}
            explain the rest.
          </p>
          <p>
            The source code is public on{" "}
            <a href={REPOSITORY_URL} className="text-ink underline">
              GitHub
            </a>
            .
          </p>
        </div>
      </section>
    </main>
  );
}
