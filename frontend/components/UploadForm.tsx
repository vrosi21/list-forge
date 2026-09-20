"use client";

import { useState } from "react";
import type { Brand } from "@/lib/api";

interface UploadFormProps {
  brands: readonly Brand[];
  busy: boolean;
  onStart: (file: File, brandId: string) => void;
}

export function UploadForm({ brands, busy, onStart }: UploadFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [brandId, setBrandId] = useState("");

  const selectedBrand = brandId || brands[0]?.id || "";
  const ready = file !== null && selectedBrand !== "" && !busy;

  return (
    <form
      className="flex flex-wrap items-end gap-4 rounded-lg border border-rule bg-surface p-4"
      onSubmit={(event) => {
        event.preventDefault();
        if (file !== null && selectedBrand !== "") {
          onStart(file, selectedBrand);
        }
      }}
    >
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-ink-soft">Catalogue CSV</span>
        <input
          type="file"
          accept=".csv,text/csv"
          required
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          className="w-72 rounded border border-rule bg-sunken px-3 py-2 text-sm file:mr-3 file:rounded file:border-0 file:bg-accent file:px-3 file:py-1 file:text-surface"
        />
      </label>

      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-ink-soft">Brand</span>
        <select
          value={selectedBrand}
          onChange={(event) => setBrandId(event.target.value)}
          disabled={brands.length === 0}
          className="w-56 rounded border border-rule bg-sunken px-3 py-2 text-sm"
        >
          {brands.map((brand) => (
            <option key={brand.id} value={brand.id}>
              {brand.name}
            </option>
          ))}
        </select>
      </label>

      <button
        type="submit"
        disabled={!ready}
        className="rounded bg-accent px-4 py-2 text-sm font-semibold text-surface disabled:opacity-40"
      >
        {busy ? "Working…" : "Start"}
      </button>
    </form>
  );
}
