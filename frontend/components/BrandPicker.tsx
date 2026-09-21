"use client";

import type { Brand } from "@/lib/api";

interface BrandPickerProps {
  brands: readonly Brand[];
  value: string;
  onChange: (brandId: string) => void;
}

export function BrandPicker({ brands, value, onChange }: BrandPickerProps) {
  const selected = brands.find((brand) => brand.id === value) ?? null;

  return (
    <div className="grid gap-6 md:grid-cols-[16rem_minmax(0,1fr)]">
      <label className="flex flex-col gap-1.5 text-sm">
        <span className="text-muted">Brand</span>
        <select
          value={value}
          onChange={(event) => onChange(event.target.value)}
          disabled={brands.length === 0}
          className="rounded border border-rule bg-surface px-3 py-2 text-sm text-ink"
        >
          {brands.map((brand) => (
            <option key={brand.id} value={brand.id}>
              {brand.name}
            </option>
          ))}
        </select>
        <span className="text-xs text-muted">
          Sets the voice and the words the copy may never use.
        </span>
      </label>

      {selected ? (
        <dl className="grid gap-3 rounded border border-rule bg-surface p-4 text-sm sm:grid-cols-2">
          <div className="sm:col-span-2">
            <dt className="text-xs text-muted">Writes for</dt>
            <dd className="text-ink">{selected.audience ?? "Not stated"}</dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-xs text-muted">Voice</dt>
            <dd className="text-ink-soft">{selected.voice}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted">Always</dt>
            <dd>
              <ul className="mt-1 flex flex-col gap-1 text-ink-soft">
                {selected.do?.map((rule) => <li key={rule}>{rule}</li>)}
              </ul>
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted">Never</dt>
            <dd>
              <ul className="mt-1 flex flex-col gap-1 text-ink-soft">
                {selected.dont?.map((rule) => <li key={rule}>{rule}</li>)}
              </ul>
            </dd>
          </div>
        </dl>
      ) : null}
    </div>
  );
}
