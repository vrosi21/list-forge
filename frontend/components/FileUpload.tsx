"use client";

import { useState } from "react";

interface FileUploadProps {
  busy: boolean;
  disabled: boolean;
  onRun: (file: File) => void;
}

export function FileUpload({ busy, disabled, onRun }: FileUploadProps) {
  const [file, setFile] = useState<File | null>(null);

  return (
    <form
      className="flex flex-wrap items-end gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        if (file !== null) {
          onRun(file);
        }
      }}
    >
      <label className="flex flex-col gap-1.5 text-sm">
        <span className="text-muted">Upload a CSV</span>
        <input
          type="file"
          accept=".csv,text/csv"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          className="w-80 rounded border border-rule bg-surface px-3 py-1.5 text-sm text-ink-soft file:mr-3 file:rounded file:border-0 file:bg-sunken file:px-3 file:py-1 file:text-ink"
        />
      </label>
      <button
        type="submit"
        disabled={file === null || busy || disabled}
        className="rounded bg-accent px-4 py-2 text-sm font-medium text-page disabled:opacity-40"
      >
        {busy ? "Starting" : "Run file"}
      </button>
    </form>
  );
}
