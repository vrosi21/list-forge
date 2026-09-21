"use client";

import type { AccessStatus } from "@/lib/api";

interface AccessBarProps {
  status: AccessStatus | null;
  code: string | null;
  onChangeCode: () => void;
}

const VISIBLE_CODE_CHARACTERS = 4;

function masked(code: string): string {
  return `${code.slice(0, VISIBLE_CODE_CHARACTERS)}${"•".repeat(4)}`;
}

function runsText(status: AccessStatus): string {
  if (status.runs_remaining === null || status.runs_remaining === undefined) {
    return "No daily limit";
  }
  const total = status.runs_per_day ?? status.runs_remaining;
  return `${status.runs_remaining} of ${total} runs left today`;
}

export function AccessBar({ status, code, onChangeCode }: AccessBarProps) {
  if (status === null) {
    return null;
  }

  if (!status.required) {
    return <p className="text-sm text-muted">This server is open. No access code needed.</p>;
  }

  if (!status.valid) {
    return (
      <div className="flex flex-wrap items-center gap-3 rounded border border-warn/40 bg-warn-soft px-4 py-3 text-sm">
        <span className="text-ink">
          {code ? "That access code is not recognised." : "Running the tool needs an access code."}
        </span>
        <button type="button" onClick={onChangeCode} className="text-ink underline">
          Enter a code
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-sm text-muted">
      <span>
        Code <span className="font-mono text-ink">{code ? masked(code) : ""}</span>
      </span>
      <span>{runsText(status)}</span>
      {status.max_rows ? <span>Up to {status.max_rows} rows per run</span> : null}
      <button type="button" onClick={onChangeCode} className="underline hover:text-ink">
        Change code
      </button>
    </div>
  );
}
