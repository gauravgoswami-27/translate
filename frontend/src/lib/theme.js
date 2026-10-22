import { useCallback, useEffect, useState } from 'react';

const KEY = 'theme';
const media = () => window.matchMedia('(prefers-color-scheme: dark)');

function apply(mode) {
  const dark = mode === 'dark' || (mode === 'system' && media().matches);
  const root = document.documentElement;
  root.classList.add('theme-transition');
  root.classList.toggle('dark', dark);
  window.setTimeout(() => root.classList.remove('theme-transition'), 250);
}

/** Theme preference: 'light' | 'dark' | 'system' (follows the OS, live). */
export function useTheme() {
  const [mode, setMode] = useState(() => {
    try {
      return localStorage.getItem(KEY) || 'system';
    } catch {
      return 'system';
    }
  });

  useEffect(() => {
    apply(mode);
    try {
      localStorage.setItem(KEY, mode);
    } catch {
      /* storage unavailable: the choice just isn't remembered */
    }
    if (mode !== 'system') return undefined;
    const mq = media();
    const onChange = () => apply('system');
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  }, [mode]);

  const cycle = useCallback(() => setMode((m) => (m === 'light' ? 'dark' : m === 'dark' ? 'system' : 'light')), []);
  return { mode, setMode, cycle };
}
