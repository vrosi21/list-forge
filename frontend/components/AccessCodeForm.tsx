"use client";

import { useState } from "react";

interface AccessCodeFormProps {
  onSubmit: (code: string) => void;
}

export function AccessCodeForm({ onSubmit }: AccessCodeFormProps) {
  const [code, setCode] = useState("");

  return (
    <form
      className="flex flex-wrap items-end gap-3 rounded-lg border border-warn/40 bg-warn-soft p-4"
      onSubmit={(event) => {
        event.preventDefault();
        if (code.trim() !== "") {
          onSubmit(code.trim());
        }
      }}
    >
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-ink">Access code</span>
        <input
          value={code}
          onChange={(event) => setCode(event.target.value)}
          placeholder="the code from your invitation link"
          className="w-72 rounded border border-rule bg-surface px-3 py-2 text-sm"
        />
      </label>
      <button
        type="submit"
        className="rounded bg-accent px-4 py-2 text-sm font-semibold text-surface"
      >
        Use code
      </button>
      <p className="w-full text-xs text-muted">
        Generating copy calls a paid model, so the demo is limited to invited reviewers. Reading
        an existing batch needs no code.
      </p>
    </form>
  );
}
