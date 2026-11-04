import type { Brand } from "@/lib/api";
import { summariseRow } from "@/lib/catalogue";
import { READY_TESTS, type ReadyTest } from "@/lib/ready-tests";

interface ReadyTestsProps {
  brands: readonly Brand[];
  startingId: string | null;
  disabled: boolean;
  onRun: (test: ReadyTest) => void;
}

export function ReadyTests({ brands, startingId, disabled, onRun }: ReadyTestsProps) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {READY_TESTS.map((test) => {
        const brand = brands.find((candidate) => candidate.id === test.brandId);

        return (
          <article
            key={test.id}
            className="flex flex-col gap-4 rounded-lg border border-rule bg-surface p-5"
          >
            <header className="flex flex-col gap-1">
              <h3 className="text-lg font-semibold text-ink">{test.title}</h3>
              <p className="text-xs text-muted">
                Brand: <span className="text-ink-soft">{brand?.name ?? test.brandId}</span> ·{" "}
                {test.rows.length} products
              </p>
            </header>

            <p className="text-sm text-ink-soft">{test.summary}</p>

            <ol className="divide-y divide-rule rounded border border-rule bg-page">
              {test.rows.map((product) => (
                <li key={product.sku} className="flex flex-col gap-0.5 px-3 py-2">
                  <span className="text-sm text-ink">{product.name}</span>
                  <span className="font-mono text-[11px] text-muted">
                    {summariseRow(product)}
                  </span>
                </li>
              ))}
            </ol>

            <footer className="mt-auto flex flex-wrap items-center justify-between gap-3">
              <p className="text-xs text-muted">{test.expectation}</p>
              <button
                type="button"
                onClick={() => onRun(test)}
                disabled={disabled || startingId !== null}
                className="rounded bg-accent px-4 py-2 text-sm font-medium text-page disabled:opacity-40"
              >
                {startingId === test.id ? "Starting" : "Run this test"}
              </button>
            </footer>
          </article>
        );
      })}
    </div>
  );
}
