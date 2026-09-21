"use client";

import { useState } from "react";
import {
  COLUMNS,
  SAMPLE_ROWS,
  filledRows,
  missingRequired,
  toCsv,
  withCell,
  withEmptyRow,
  withoutRow,
  type CatalogueRow,
} from "@/lib/catalogue";

interface CatalogueEditorProps {
  maxRows: number;
  busy: boolean;
  disabled: boolean;
  onRun: (file: File) => void;
}

const FILE_NAME = "example-catalogue.csv";

function download(csv: string): void {
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = FILE_NAME;
  link.click();
  URL.revokeObjectURL(url);
}

function rowNumbers(indexes: readonly number[]): string {
  return indexes.map((index) => index + 1).join(", ");
}

export function CatalogueEditor({ maxRows, busy, disabled, onRun }: CatalogueEditorProps) {
  const [rows, setRows] = useState<CatalogueRow[]>(() => SAMPLE_ROWS.slice(0, maxRows));

  const filled = filledRows(rows);
  const incomplete = missingRequired(filled);
  const overLimit = filled.length > maxRows;
  const runnable = filled.length > 0 && incomplete.length === 0 && !overLimit;

  return (
    <details className="group rounded border border-rule bg-surface">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-4 px-4 py-3 text-sm">
        <span>
          <span className="font-medium text-ink">Or edit the example table</span>
          <span className="ml-2 text-muted">No file needed. Change any cell and run it.</span>
        </span>
        <span className="text-xs text-muted group-open:hidden">Show</span>
        <span className="hidden text-xs text-muted group-open:inline">Hide</span>
      </summary>

      <div className="flex flex-col gap-3 border-t border-rule p-4">
        <p className="text-xs text-muted">
          One row per product. Empty cells mean unknown, and the model is told not to fill them
          in. Put several stones, colours or materials in one cell separated by a semicolon. Up
          to {maxRows} rows.
        </p>

        <div className="overflow-x-auto">
          <table className="border-collapse text-xs">
            <thead>
              <tr>
                {COLUMNS.map((column) => (
                  <th
                    key={column.key}
                    scope="col"
                    className="border-b border-rule px-1 pb-2 text-left font-medium text-muted"
                  >
                    {column.label}
                  </th>
                ))}
                <th scope="col" className="border-b border-rule" />
              </tr>
            </thead>
            <tbody>
              {rows.map((current, index) => (
                <tr key={index}>
                  {COLUMNS.map((column) => (
                    <td key={column.key} className="px-1 py-1">
                      <input
                        value={current[column.key]}
                        placeholder={column.hint}
                        aria-label={`Row ${index + 1} ${column.label}`}
                        onChange={(event) =>
                          setRows(withCell(rows, index, column.key, event.target.value))
                        }
                        className={`${column.width} rounded border border-rule bg-page px-2 py-1 font-mono text-ink placeholder:text-muted/50`}
                      />
                    </td>
                  ))}
                  <td className="px-1 py-1">
                    <button
                      type="button"
                      onClick={() => setRows(withoutRow(rows, index))}
                      className="px-2 py-1 text-muted hover:text-bad"
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {incomplete.length > 0 ? (
          <p className="text-xs text-bad">
            {incomplete.length === 1 ? "Row" : "Rows"} {rowNumbers(incomplete)}{" "}
            {incomplete.length === 1 ? "needs" : "need"} a SKU and a name.
          </p>
        ) : null}

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setRows(withEmptyRow(rows, maxRows))}
            disabled={rows.length >= maxRows}
            className="rounded border border-rule px-3 py-1.5 text-sm text-ink-soft hover:border-rule-strong disabled:opacity-40"
          >
            Add row
          </button>
          <button
            type="button"
            onClick={() => setRows(SAMPLE_ROWS.slice(0, maxRows))}
            className="rounded border border-rule px-3 py-1.5 text-sm text-ink-soft hover:border-rule-strong"
          >
            Reset
          </button>
          <button
            type="button"
            onClick={() => download(toCsv(filled))}
            disabled={filled.length === 0}
            className="rounded border border-rule px-3 py-1.5 text-sm text-ink-soft hover:border-rule-strong disabled:opacity-40"
          >
            Download CSV
          </button>
          <button
            type="button"
            onClick={() => onRun(new File([toCsv(filled)], FILE_NAME, { type: "text/csv" }))}
            disabled={!runnable || busy || disabled}
            className="ml-auto rounded bg-accent px-4 py-1.5 text-sm font-medium text-page disabled:opacity-40"
          >
            {busy ? "Starting" : "Run table"}
          </button>
        </div>
      </div>
    </details>
  );
}
