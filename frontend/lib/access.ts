const STORAGE_KEY = "listforge.access-code";
const FRAGMENT_KEY = "code";

export function readAccessCode(): string | null {
  const fromLink = codeFromFragment();
  if (fromLink !== null) {
    storeAccessCode(fromLink);
    stripFragment();
    return fromLink;
  }
  return storedAccessCode();
}

export function storeAccessCode(code: string): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, code);
  } catch {
    return;
  }
}

export function clearAccessCode(): void {
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    return;
  }
}

function storedAccessCode(): string | null {
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function codeFromFragment(): string | null {
  if (typeof window === "undefined" || !window.location.hash) {
    return null;
  }
  const code = new URLSearchParams(window.location.hash.slice(1)).get(FRAGMENT_KEY);
  return code !== null && code.trim() !== "" ? code.trim() : null;
}

function stripFragment(): void {
  window.history.replaceState(null, "", window.location.pathname + window.location.search);
}
