import { useCallback, useEffect, useState } from 'react';

const STORAGE_KEY = 'jh_theme';
const VALID = ['system', 'light', 'dark'];

const readInitial = () => {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    return VALID.includes(v) ? v : 'system';
  } catch {
    return 'system';
  }
};

const prefersDark = () => {
  if (typeof window === 'undefined' || !window.matchMedia) return false;
  return window.matchMedia('(prefers-color-scheme: dark)').matches;
};

const apply = (theme) => {
  const effective = theme === 'system' ? (prefersDark() ? 'dark' : 'light') : theme;
  document.documentElement.setAttribute('data-theme', effective);
  return effective;
};

export default function useTheme() {
  const [theme, setThemeState] = useState(readInitial);
  const [effective, setEffective] = useState(() => apply(readInitial()));

  useEffect(() => {
    setEffective(apply(theme));
    try { localStorage.setItem(STORAGE_KEY, theme); } catch { /* ignore */ }
  }, [theme]);

  useEffect(() => {
    if (theme !== 'system' || !window.matchMedia) return undefined;
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = () => setEffective(apply('system'));
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  }, [theme]);

  const setTheme = useCallback((next) => {
    if (VALID.includes(next)) setThemeState(next);
  }, []);

  const cycle = useCallback(() => {
    setThemeState((prev) => {
      const idx = VALID.indexOf(prev);
      return VALID[(idx + 1) % VALID.length];
    });
  }, []);

  return { theme, effective, setTheme, cycle };
}
