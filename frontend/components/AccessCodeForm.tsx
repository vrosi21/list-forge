"use client";

import { useState } from "react";

interface AccessCodeFormProps {
  onSubmit: (code: string) => void;
  submitLabel?: string;
}

export function AccessCodeForm({ onSubmit, submitLabel = "Use code" }: AccessCodeFormProps) {
  const [code, setCode] = useState("");

  return (
    <form
      className="flex flex-wrap items-end gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        if (code.trim() !== "") {
          onSubmit(code.trim());
        }
      }}
    >
      <label className="flex flex-col gap-1.5 text-sm">
        <span className="text-muted">Access code</span>
        <input
          value={code}
          onChange={(event) => setCode(event.target.value)}
          placeholder="from your invitation link"
          autoComplete="off"
          spellCheck={false}
          className="w-64 rounded border border-rule bg-surface px-3 py-2 font-mono text-sm text-ink placeholder:font-sans placeholder:text-muted"
        />
      </label>
      <button
        type="submit"
        disabled={code.trim() === ""}
        className="rounded bg-accent px-4 py-2 text-sm font-medium text-page disabled:opacity-40"
      >
        {submitLabel}
      </button>
    </form>
  );
}
