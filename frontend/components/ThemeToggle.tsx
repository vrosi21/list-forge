"use client";

import { THEME_STORAGE_KEY } from "@/lib/site";

function nextTheme(): "light" | "dark" {
  return document.documentElement.dataset.theme === "dark" ? "light" : "dark";
}

export function ThemeToggle() {
  return (
    <button
      type="button"
      onClick={() => {
        const theme = nextTheme();
        document.documentElement.dataset.theme = theme;
        try {
          window.localStorage.setItem(THEME_STORAGE_KEY, theme);
        } catch {
          return;
        }
      }}
      className="rounded border border-rule px-2.5 py-1 text-xs text-ink-soft hover:border-rule-strong hover:text-ink"
    >
      <span className="theme-to-dark">Dark</span>
      <span className="theme-to-light">Light</span>
    </button>
  );
}
