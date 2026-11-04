"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ApiError,
  UNAUTHORIZED,
  checkAccess,
  createBatch,
  listBrands,
  readBatch,
  readHealth,
  regenerateItem,
  type AccessStatus,
  type BatchResponse,
  type Brand,
  type Health,
} from "@/lib/api";
import { readAccessCode, storeAccessCode } from "@/lib/access";
import {
  countFor,
  firstPopulatedTab,
  itemsFor,
  progressOf,
  TAB_STATUSES,
  type TabStatus,
} from "@/lib/batch";
import { DEFAULT_MAX_ROWS } from "@/lib/catalogue";
import { readyTestFile, type ReadyTest } from "@/lib/ready-tests";
import { AccessBar } from "@/components/AccessBar";
import { AccessCodeForm } from "@/components/AccessCodeForm";
import { BrandPicker } from "@/components/BrandPicker";
import { CatalogueEditor } from "@/components/CatalogueEditor";
import { CostCounter } from "@/components/CostCounter";
import { FileUpload } from "@/components/FileUpload";
import { ItemTable } from "@/components/ItemTable";
import { OutcomeExamples } from "@/components/OutcomeExamples";
import { ProgressBar } from "@/components/ProgressBar";
import { ProviderBadge } from "@/components/ProviderBadge";
import { ReadyTests } from "@/components/ReadyTests";
import { ReviewPanel } from "@/components/ReviewPanel";
import { StatusTabs } from "@/components/StatusTabs";

const POLL_INTERVAL_MS = 1000;
const OWN_FILE = "own-file";
const OWN_TABLE = "own-table";

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : "the request failed";
}

function SectionHeading({ title, lede }: { title: string; lede: string }) {
  return (
    <div className="flex flex-col gap-1">
      <h2 className="text-xl font-semibold tracking-tight text-ink">{title}</h2>
      <p className="max-w-2xl text-sm text-ink-soft">{lede}</p>
    </div>
  );
}

export function ToolScreen() {
  const [brands, setBrands] = useState<Brand[]>([]);
  const [brandId, setBrandId] = useState("");
  const [health, setHealth] = useState<Health | null>(null);
  const [accessCode, setAccessCode] = useState<string | null>(null);
  const [access, setAccess] = useState<AccessStatus | null>(null);
  const [codeFormOpen, setCodeFormOpen] = useState(false);
  const [batchId, setBatchId] = useState<string | null>(null);
  const [batch, setBatch] = useState<BatchResponse | null>(null);
  const [tab, setTab] = useState<TabStatus>(TAB_STATUSES[0]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [startingId, setStartingId] = useState<string | null>(null);
  const [runLabel, setRunLabel] = useState<string | null>(null);
  const [regenerating, setRegenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const resultsRef = useRef<HTMLElement>(null);

  const refreshAccess = useCallback(async (code: string | null) => {
    try {
      setAccess(await checkAccess(code));
    } catch (cause) {
      setError(messageOf(cause));
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const code = readAccessCode();

    void (async () => {
      try {
        const [loadedBrands, loadedHealth, loadedAccess] = await Promise.all([
          listBrands(controller.signal),
          readHealth(controller.signal),
          checkAccess(code, controller.signal),
        ]);
        setAccessCode(code);
        setBrands(loadedBrands);
        setBrandId((current) => current || loadedBrands[0]?.id || "");
        setHealth(loadedHealth);
        setAccess(loadedAccess);
        setCodeFormOpen(loadedAccess.required && !loadedAccess.valid);
      } catch (cause) {
        if (!controller.signal.aborted) {
          setError(messageOf(cause));
        }
      }
    })();

    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (batchId === null) {
      return;
    }

    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;

    const poll = async () => {
      try {
        const next = await readBatch(batchId, controller.signal);
        if (controller.signal.aborted) {
          return;
        }
        setBatch(next);
        setTab((current) =>
          countFor(next.counts, current) > 0 ? current : firstPopulatedTab(next.counts),
        );
        if (progressOf(next.counts).running) {
          timer = setTimeout(() => void poll(), POLL_INTERVAL_MS);
        }
      } catch (cause) {
        if (!controller.signal.aborted) {
          setError(messageOf(cause));
        }
      }
    };

    void poll();

    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [batchId]);

  const brandNameOf = useCallback(
    (id: string) => brands.find((brand) => brand.id === id)?.name ?? id,
    [brands],
  );

  const start = useCallback(
    async (file: File, runBrandId: string, sourceId: string, label: string) => {
      setStartingId(sourceId);
      setError(null);
      try {
        const created = await createBatch(file, runBrandId, accessCode);
        setBatch(null);
        setSelectedId(null);
        setTab(TAB_STATUSES[0]);
        setRunLabel(label);
        setBatchId(created);
        resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      } catch (cause) {
        setCodeFormOpen(cause instanceof ApiError && cause.status === UNAUTHORIZED);
        setError(messageOf(cause));
      } finally {
        setStartingId(null);
        void refreshAccess(accessCode);
      }
    },
    [accessCode, refreshAccess],
  );

  const runReadyTest = useCallback(
    (test: ReadyTest) =>
      void start(
        readyTestFile(test),
        test.brandId,
        test.id,
        `${test.title} · ${brandNameOf(test.brandId)}`,
      ),
    [brandNameOf, start],
  );

  const runOwn = useCallback(
    (file: File, sourceId: string) =>
      void start(file, brandId, sourceId, `Your products · ${brandNameOf(brandId)}`),
    [brandId, brandNameOf, start],
  );

  const regenerate = useCallback(
    async (itemId: string) => {
      setRegenerating(true);
      setError(null);
      try {
        await regenerateItem(itemId, accessCode);
        if (batchId !== null) {
          setBatch(await readBatch(batchId));
        }
      } catch (cause) {
        setCodeFormOpen(cause instanceof ApiError && cause.status === UNAUTHORIZED);
        setError(messageOf(cause));
      } finally {
        setRegenerating(false);
        void refreshAccess(accessCode);
      }
    },
    [accessCode, batchId, refreshAccess],
  );

  const applyCode = useCallback(
    (code: string) => {
      storeAccessCode(code);
      setAccessCode(code);
      setCodeFormOpen(false);
      setError(null);
      void refreshAccess(code);
    },
    [refreshAccess],
  );

  const blocked = access !== null && access.required && !access.valid;
  const maxRows = access?.max_rows ?? DEFAULT_MAX_ROWS;
  const selected = batch?.items.find((item) => item.id === selectedId) ?? null;

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-14 px-6 py-10">
      <header className="flex flex-col gap-4">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="flex flex-col gap-1">
            <h1 className="text-2xl font-semibold tracking-tight text-ink">Generate and review</h1>
            <p className="max-w-2xl text-ink-soft">
              A model writes the listing, then code checks every claim against the product row.
              Start with a ready test, or try your own products at the bottom. Nothing here is
              published anywhere.
            </p>
          </div>
          <ProviderBadge health={health} />
        </div>
        <AccessBar
          status={access}
          code={accessCode}
          onChangeCode={() => setCodeFormOpen(true)}
        />
        {codeFormOpen ? <AccessCodeForm onSubmit={applyCode} /> : null}
      </header>

      <section className="flex flex-col gap-5">
        <SectionHeading
          title="What comes back"
          lede="Every product ends in one of three states. The two samples are real results from this deployment, shown exactly as the model wrote them."
        />
        <OutcomeExamples brands={brands} />
      </section>

      <section className="flex flex-col gap-5">
        <SectionHeading
          title="Run a ready test"
          lede="Two small catalogues, one per brand. Each run sends one request per product, so it takes a few seconds. A row that has run before comes from the cache at no cost."
        />
        <ReadyTests
          brands={brands}
          startingId={startingId}
          disabled={blocked}
          onRun={runReadyTest}
        />
      </section>

      {error !== null ? (
        <p role="alert" className="rounded border border-bad/30 bg-bad-soft px-4 py-3 text-sm text-bad">
          {error}
        </p>
      ) : null}

      <section ref={resultsRef} className="flex scroll-mt-6 flex-col gap-6">
        {batch !== null ? (
          <>
            <SectionHeading
              title="Results"
              lede={`${runLabel ?? "Your run"}. Pick a row to see the product facts beside the copy, with every finding marked.`}
            />
            <div className="rounded border border-rule bg-surface p-4">
              <ProgressBar progress={progressOf(batch.counts)} />
            </div>

            <CostCounter totals={batch.totals} />

            <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
              <div className="overflow-hidden rounded border border-rule bg-surface">
                <StatusTabs counts={batch.counts} active={tab} onSelect={setTab} />
                <ItemTable
                  items={itemsFor(batch.items, tab)}
                  selectedId={selectedId}
                  onSelect={setSelectedId}
                />
              </div>

              <ReviewPanel
                item={selected}
                regenerating={regenerating}
                onRegenerate={(itemId) => void regenerate(itemId)}
              />
            </div>
          </>
        ) : null}
      </section>

      <section className="flex flex-col gap-5 border-t border-rule pt-10">
        <SectionHeading
          title="Use your own products"
          lede="Pick a brand, then upload a CSV or edit a table here. One row per product. Only SKU and name are required, and an empty cell means the fact is unknown."
        />
        <BrandPicker brands={brands} value={brandId} onChange={setBrandId} />
        <div className="flex flex-col gap-3 rounded-lg border border-rule bg-surface p-5">
          <FileUpload
            busy={startingId === OWN_FILE}
            disabled={blocked || brandId === "" || startingId !== null}
            onRun={(file) => runOwn(file, OWN_FILE)}
          />
          <p className="text-xs text-muted">
            Columns: sku, name, product_type, stones, colours, materials, size_mm, weight_g,
            pieces, origin, price_eur. Separate several values in one cell with a semicolon. Up
            to {maxRows} rows.
          </p>
        </div>
        <CatalogueEditor
          maxRows={maxRows}
          busy={startingId === OWN_TABLE}
          disabled={blocked || brandId === "" || startingId !== null}
          onRun={(file) => runOwn(file, OWN_TABLE)}
        />
      </section>
    </main>
  );
}
