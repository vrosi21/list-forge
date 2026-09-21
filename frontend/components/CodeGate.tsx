"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { checkAccess, type AccessStatus } from "@/lib/api";
import { clearAccessCode, readAccessCode, storeAccessCode } from "@/lib/access";
import { AccessCodeForm } from "@/components/AccessCodeForm";

type Gate =
  | { kind: "checking" }
  | { kind: "needed" }
  | { kind: "invalid" }
  | { kind: "offline" }
  | { kind: "ready"; status: AccessStatus };

async function evaluate(code: string | null): Promise<Gate> {
  try {
    const status = await checkAccess(code);
    if (!status.required || status.valid) {
      return { kind: "ready", status };
    }
    return code ? { kind: "invalid" } : { kind: "needed" };
  } catch {
    return { kind: "offline" };
  }
}

function runsLine(status: AccessStatus): string {
  if (!status.required) {
    return "This server is open, so no code is needed.";
  }
  if (status.runs_remaining === null || status.runs_remaining === undefined) {
    return "Your code is accepted.";
  }
  const total = status.runs_per_day ?? status.runs_remaining;
  return `Your code is accepted. ${status.runs_remaining} of ${total} runs left today.`;
}

export function CodeGate() {
  const [gate, setGate] = useState<Gate>({ kind: "checking" });

  useEffect(() => {
    let active = true;
    const refresh = () => {
      void evaluate(readAccessCode()).then((next) => {
        if (active) {
          setGate(next);
        }
      });
    };

    refresh();
    window.addEventListener("hashchange", refresh);
    return () => {
      active = false;
      window.removeEventListener("hashchange", refresh);
    };
  }, []);

  const tryCode = (code: string) => {
    storeAccessCode(code);
    setGate({ kind: "checking" });
    void evaluate(code).then((next) => {
      if (next.kind === "invalid") {
        clearAccessCode();
      }
      setGate(next);
    });
  };

  return (
    <div className="flex flex-col gap-4 rounded border border-rule bg-surface p-5">
      <h2 className="text-sm font-medium text-ink">Access</h2>

      {gate.kind === "checking" ? <p className="text-sm text-muted">Checking your access.</p> : null}

      {gate.kind === "ready" ? (
        <>
          <p className="text-sm text-ink-soft">{runsLine(gate.status)}</p>
          <Link
            href="/tool"
            className="self-start rounded bg-accent px-4 py-2 text-sm font-medium text-page"
          >
            Open the tool
          </Link>
        </>
      ) : null}

      {gate.kind === "needed" || gate.kind === "invalid" ? (
        <>
          <p className="text-sm text-ink-soft">
            {gate.kind === "invalid"
              ? "That code was not recognised. Check the link you were sent."
              : "Each run calls a paid model, so the tool is open to invited reviewers. Your code is at the end of the link you were sent, after #code=."}
          </p>
          <AccessCodeForm onSubmit={tryCode} submitLabel="Continue" />
        </>
      ) : null}

      {gate.kind === "offline" ? (
        <p className="text-sm text-ink-soft">
          The server did not answer. It may be restarting, so try again in a minute.
        </p>
      ) : null}
    </div>
  );
}
