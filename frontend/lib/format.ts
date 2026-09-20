const USD_FRACTION_DIGITS = 4;
const EMPTY = "—";

const integers = new Intl.NumberFormat("en-GB");
const timestamps = new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short" });

export function formatUsd(amount: string | null | undefined): string {
  if (amount === null || amount === undefined) {
    return EMPTY;
  }
  const value = Number(amount);
  return Number.isFinite(value) ? `$${value.toFixed(USD_FRACTION_DIGITS)}` : EMPTY;
}

export function formatInteger(value: number): string {
  return integers.format(value);
}

export function formatTimestamp(value: string | null | undefined): string {
  if (value === null || value === undefined) {
    return EMPTY;
  }
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? EMPTY : timestamps.format(parsed);
}

export function formatFact(value: string | number | string[] | null | undefined): string {
  if (Array.isArray(value)) {
    return value.length > 0 ? value.join(", ") : EMPTY;
  }
  if (value === null || value === undefined || value === "") {
    return EMPTY;
  }
  return String(value);
}

export function formatFieldName(field: string): string {
  const bullet = /^bullets\[(\d+)\]$/.exec(field);
  if (bullet) {
    return `Bullet ${Number(bullet[1]) + 1}`;
  }
  return field.replace(/_/g, " ").replace(/^./, (character) => character.toUpperCase());
}

export function formatStatus(status: string): string {
  return formatFieldName(status);
}
