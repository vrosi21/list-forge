"use client";

import { useCallback, useEffect, useState } from "react";
import {
  createBatch,
  listBrands,
  readBatch,
  readHealth,
  regenerateItem,
  type BatchResponse,
  type Brand,
  type Health,
} from "@/lib/api";
import { itemsFor, progressOf, TAB_STATUSES, type TabStatus } from "@/lib/batch";
import { CostCounter } from "@/components/CostCounter";
import { ItemTable } from "@/components/ItemTable";
import { ProgressBar } from "@/components/ProgressBar";
import { ProviderBadge } from "@/components/ProviderBadge";
import { ReviewPanel } from "@/components/ReviewPanel";
import { StatusTabs } from "@/components/StatusTabs";
import { UploadForm } from "@/components/UploadForm";

const POLL_INTERVAL_MS = 1000;

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : "the request failed";
}

export default function Home() {
  const [brands, setBrands] = useState<Brand[]>([]);
  const [health, setHealth] = useState<Health | null>(null);
  const [batchId, setBatchId] = useState<string | null>(null);
  const [batch, setBatch] = useState<BatchResponse | null>(null);
  const [tab, setTab] = useState<TabStatus>(TAB_STATUSES[0]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    void (async () => {
      try {
        const [loadedBrands, loadedHealth] = await Promise.all([
          listBrands(controller.signal),
          readHealth(controller.signal),
        ]);
        setBrands(loadedBrands);
        setHealth(loadedHealth);
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

  const start = useCallback(async (file: File, brandId: string) => {
    setStarting(true);
    setError(null);
    try {
      const created = await createBatch(file, brandId);
      setBatch(null);
      setSelectedId(null);
      setBatchId(created);
    } catch (cause) {
      setError(messageOf(cause));
    } finally {
      setStarting(false);
    }
  }, []);

  const regenerate = useCallback(
    async (itemId: string) => {
      setRegenerating(true);
      setError(null);
      try {
        await regenerateItem(itemId);
        if (batchId !== null) {
          setBatch(await readBatch(batchId));
        }
      } catch (cause) {
        setError(messageOf(cause));
      } finally {
        setRegenerating(false);
      }
    },
    [batchId],
  );

  const selected = batch?.items.find((item) => item.id === selectedId) ?? null;

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-6 py-8">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">ListForge</h1>
          <p className="text-sm text-muted">
            The model proposes copy. Checks against the catalogue decide where it goes.
          </p>
        </div>
        <ProviderBadge health={health} />
      </header>

      <UploadForm brands={brands} busy={starting} onStart={(file, brandId) => void start(file, brandId)} />

      {error !== null ? (
        <p role="alert" className="rounded border border-bad/40 bg-bad-soft px-4 py-3 text-sm text-bad">
          {error}
        </p>
      ) : null}

      {batch !== null ? (
        <div className="flex flex-col gap-6">
          <div className="rounded-lg border border-rule bg-surface p-4">
            <ProgressBar progress={progressOf(batch.counts)} />
          </div>

          <CostCounter totals={batch.totals} />

          <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
            <div className="overflow-hidden rounded-lg border border-rule bg-surface">
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
        </div>
      ) : null}
    </main>
  );
}
