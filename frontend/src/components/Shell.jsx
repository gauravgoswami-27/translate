import { useEffect, useRef, useState } from 'react';
import { BarChart3, BookOpen, Columns3, Languages, LibraryBig, Monitor, Moon, Sun, Zap } from 'lucide-react';
import { cx } from './ui';

export const PAGES = [
  { id: 'translate', label: 'Translate', icon: Languages },
  { id: 'compare', label: 'Compare', icon: Columns3 },
  { id: 'results', label: 'Results', icon: BarChart3 },
  { id: 'glossary', label: 'Glossary', icon: LibraryBig },
  { id: 'reader', label: 'Course reader', icon: BookOpen },
];

const THEME_OPTIONS = [
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'dark', label: 'Dark', icon: Moon },
  { value: 'system', label: 'System', icon: Monitor },
];

function ThemeToggle({ mode, setMode }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const Current = THEME_OPTIONS.find((o) => o.value === mode)?.icon ?? Monitor;
  useEffect(() => {
    if (!open) return undefined;
    const close = (e) => {
      if (e.type === 'keydown' ? e.key === 'Escape' : !ref.current?.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', close);
    document.addEventListener('keydown', close);
    return () => {
      document.removeEventListener('mousedown', close);
      document.removeEventListener('keydown', close);
    };
  }, [open]);
  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        aria-label={`Theme: ${mode}`}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="grid h-9 w-9 cursor-pointer place-items-center rounded-xl border border-line bg-surface text-ink-2 transition hover:text-ink"
      >
        <Current className="h-4 w-4" />
      </button>
      {open && (
        <div role="menu" className="absolute right-0 top-11 z-50 w-36 overflow-hidden rounded-xl border border-line bg-surface p-1 shadow-card">
          {THEME_OPTIONS.map(({ value, label, icon: Icon }) => (
            <button
              key={value}
              role="menuitemradio"
              aria-checked={mode === value}
              onClick={() => {
                setMode(value);
                setOpen(false);
              }}
              className={cx(
                'flex w-full cursor-pointer items-center gap-2 rounded-lg px-2.5 py-2 text-sm transition',
                mode === value ? 'bg-accent-soft text-accent' : 'text-ink-2 hover:bg-raised hover:text-ink',
              )}
            >
              <Icon className="h-4 w-4" /> {label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function ApiStatus({ health }) {
  const online = health.status === 'online';
  const label = health.status === 'checking' ? 'Checking API…' : online ? `API online · ${health.data.device.toUpperCase()}` : 'API offline';
  return (
    <span
      className="hidden items-center gap-2 rounded-xl border border-line bg-surface px-3 py-1.5 text-xs text-ink-2 sm:inline-flex"
      title={online ? `Loaded models: ${Object.keys(health.data.models_loaded).join(', ') || 'none yet'}` : undefined}
    >
      <span className={cx('h-2 w-2 rounded-full', online ? 'bg-good' : health.status === 'checking' ? 'bg-ink-3' : 'bg-warn')} aria-hidden />
      {label}
    </span>
  );
}

export function Shell({ page, setPage, theme, health, children }) {
  return (
    <div className="flex min-h-screen flex-col">
      <header
        className="sticky top-0 z-40 border-b border-line bg-canvas/85 backdrop-blur-md"
        style={{ paddingTop: 'env(safe-area-inset-top, 0px)' }}
      >
        <div className="mx-auto flex h-16 max-w-6xl items-center gap-4 px-4 sm:px-6">
          <a href="#translate" className="flex shrink-0 items-center gap-2.5" onClick={() => setPage('translate')}>
            <span className="grid h-8 w-8 place-items-center rounded-lg bg-accent text-accent-ink">
              <Zap className="h-4 w-4" fill="currentColor" />
            </span>
            <span className="leading-tight">
              <span className="block text-[15px] font-semibold tracking-tight">IndicVocational</span>
              <span className="hidden text-[11px] text-ink-3 sm:block">Electrician content localization</span>
            </span>
          </a>
          <nav className="mx-auto hidden items-center gap-1 md:flex" aria-label="Main">
            {PAGES.map(({ id, label, icon: Icon }) => (
              <a
                key={id}
                href={`#${id}`}
                aria-current={page === id ? 'page' : undefined}
                className={cx(
                  'inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium transition',
                  page === id ? 'bg-surface text-ink shadow-card' : 'text-ink-2 hover:text-ink',
                )}
              >
                <Icon className="h-4 w-4" aria-hidden />
                {label}
              </a>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2 md:ml-0">
            <ApiStatus health={health} />
            <ThemeToggle mode={theme.mode} setMode={theme.setMode} />
          </div>
        </div>
        <nav className="flex gap-1 overflow-x-auto px-4 pb-2 md:hidden" aria-label="Main">
          {PAGES.map(({ id, label, icon: Icon }) => (
            <a
              key={id}
              href={`#${id}`}
              aria-current={page === id ? 'page' : undefined}
              className={cx(
                'inline-flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-[13px] font-medium',
                page === id ? 'bg-surface text-ink shadow-card' : 'text-ink-2',
              )}
            >
              <Icon className="h-3.5 w-3.5" aria-hidden />
              {label}
            </a>
          ))}
        </nav>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6 sm:py-10">{children}</main>

      <footer className="border-t border-line" style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}>
        <div className="mx-auto flex max-w-6xl flex-col gap-1 px-4 py-6 text-xs text-ink-3 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <p>Research prototype: terminology-aware distillation of IndicTrans2 for vocational content.</p>
          <p>Base models by AI4Bharat (IndicTrans2). Source texts: NIMI Electrician trade books.</p>
        </div>
      </footer>
    </div>
  );
}
