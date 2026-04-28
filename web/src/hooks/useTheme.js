import { useCallback, useEffect, useState } from 'react';

const STORAGE_KEY = 'jh_theme';
const VALID = ['light', 'dark'];

const prefersDark = () => {
  if (typeof window === 'undefined' || !window.matchMedia) return false;
  return window.matchMedia('(prefers-color-scheme: dark)').matches;
};

const readInitial = () => {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    if (VALID.includes(v)) return v;
  } catch { /* ignore */ }
  return prefersDark() ? 'dark' : 'light';
};

const apply = (theme) => {
  document.documentElement.setAttribute('data-theme', theme);
};

export default function useTheme() {
  const [theme, setThemeState] = useState(readInitial);

  useEffect(() => {
    apply(theme);
    try { localStorage.setItem(STORAGE_KEY, theme); } catch { /* ignore */ }
  }, [theme]);

  const setTheme = useCallback((next) => {
    if (VALID.includes(next)) setThemeState(next);
  }, []);

  const toggle = useCallback(() => {
    setThemeState((prev) => (prev === 'dark' ? 'light' : 'dark'));
  }, []);

  return { theme, setTheme, toggle };
}
