import { useEffect, useState } from 'react';

type Theme = 'light' | 'dark';
const THEME_KEY = 'clip-theme';

/** Read the saved display preference, falling back to the browser's color scheme. */
function initialTheme(): Theme {
  try {
    const saved = window.localStorage.getItem(THEME_KEY);
    if (saved === 'light' || saved === 'dark') return saved;
  } catch {
    // The theme remains usable when browser storage is blocked.
  }
  return window.matchMedia?.('(prefers-color-scheme: dark)')?.matches ? 'dark' : 'light';
}

/** Apply the saved or system palette before the app mounts, including callback pages. */
export function initializeTheme(): void {
  document.documentElement.dataset.theme = initialTheme();
}

/** Switch the shared palette without changing account data or requiring storage access. */
export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(initialTheme);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  function toggleTheme() {
    const next = theme === 'light' ? 'dark' : 'light';
    setTheme(next);
    try {
      window.localStorage.setItem(THEME_KEY, next);
    } catch {
      // A private browsing policy may disable persistence; keep the current selection.
    }
  }

  return <button type="button" className="app-shell__theme" onClick={toggleTheme}
    aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}>
    {theme === 'light' ? (
      <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M20.4 14.5A8.7 8.7 0 0 1 9.5 3.6 8.7 8.7 0 1 0 20.4 14.5Z" />
      </svg>
    ) : (
      <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="4" />
        <path d="M12 2v2m0 16v2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M2 12h2m16 0h2M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42" />
      </svg>
    )}
  </button>;
}
