// Light default (SURU rule: never dark-by-default). Persisted per browser.
const THEME_KEY = "argos_theme";
export type Theme = "light" | "dark";

export function getTheme(): Theme {
  return (localStorage.getItem(THEME_KEY) as Theme) ?? "light";
}

export function applyTheme(theme: Theme): void {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem(THEME_KEY, theme);
}

export function toggleTheme(): Theme {
  const next: Theme = getTheme() === "dark" ? "light" : "dark";
  applyTheme(next);
  return next;
}
