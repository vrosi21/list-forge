"use client";

import { useCallback, useEffect, useState } from "react";
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
import { itemsFor, progressOf, TAB_STATUSES, type TabStatus } from "@/lib/batch";
import { DEFAULT_MAX_ROWS } from "@/lib/catalogue";
import { AccessBar } from "@/components/AccessBar";
import { AccessCodeForm } from "@/components/AccessCodeForm";
import { BrandPicker } from "@/components/BrandPicker";
import { CatalogueEditor } from "@/components/CatalogueEditor";
import { CostCounter } from "@/components/CostCounter";
import { FileUpload } from "@/components/FileUpload";
import { ItemTable } from "@/components/ItemTable";
import { ProgressBar } from "@/components/ProgressBar";
import { ProviderBadge } from "@/components/ProviderBadge";
import { ReviewPanel } from "@/components/ReviewPanel";
import { StatusTabs } from "@/components/StatusTabs";

const POLL_INTERVAL_MS = 1000;

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : "the request failed";
}

function StepHeading({ number, title }: { number: string; title: string }) {
  return (
    <h2 className="flex items-baseline gap-3 text-sm font-medium text-ink">
      <span className="font-mono text-xs text-muted">{number}</span>
      {title}
    </h2>
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
  const [starting, setStarting] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  const start = useCallback(
    async (file: File) => {
      setStarting(true);
      setError(null);
      try {
        const created = await createBatch(file, brandId, accessCode);
        setBatch(null);
        setSelectedId(null);
        setBatchId(created);
      } catch (cause) {
        setCodeFormOpen(cause instanceof ApiError && cause.status === UNAUTHORIZED);
        setError(messageOf(cause));
      } finally {
        setStarting(false);
        void refreshAccess(accessCode);
      }
    },
    [accessCode, brandId, refreshAccess],
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
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-10 px-6 py-10">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold tracking-tight text-ink">Generate and review</h1>
          <p className="max-w-2xl text-ink-soft">
            Pick a brand, give it a few products, then read what comes back. Every claim in the
            copy is checked against the product row. Nothing here is published anywhere.
          </p>
        </div>
        <ProviderBadge health={health} />
      </header>

      <div className="flex flex-col gap-3">
        <AccessBar
          status={access}
          code={accessCode}
          onChangeCode={() => setCodeFormOpen(true)}
        />
        {codeFormOpen ? <AccessCodeForm onSubmit={applyCode} /> : null}
      </div>

      <section className="flex flex-col gap-4">
        <StepHeading number="01" title="Choose a brand" />
        <BrandPicker brands={brands} value={brandId} onChange={setBrandId} />
      </section>

      <section className="flex flex-col gap-4">
        <StepHeading number="02" title="Give it products" />
        <FileUpload busy={starting} disabled={blocked || brandId === ""} onRun={(file) => void start(file)} />
        <CatalogueEditor
          maxRows={maxRows}
          busy={starting}
          disabled={blocked || brandId === ""}
          onRun={(file) => void start(file)}
        />
      </section>

      {error !== null ? (
        <p role="alert" className="rounded border border-bad/30 bg-bad-soft px-4 py-3 text-sm text-bad">
          {error}
        </p>
      ) : null}

      {batch !== null ? (
        <section className="flex flex-col gap-6">
          <StepHeading number="03" title="Review the results" />
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
        </section>
      ) : null}
    </main>
  );
}
