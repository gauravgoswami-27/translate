import { AlertTriangle, CheckCircle2, ChevronDown, Info, Loader2, XCircle } from 'lucide-react';

export function cx(...classes) {
  return classes.filter(Boolean).join(' ');
}

export function Card({ className, children, ...props }) {
  return (
    <section className={cx('rounded-2xl border border-line bg-surface shadow-card', className)} {...props}>
      {children}
    </section>
  );
}

export function CardHeader({ title, subtitle, icon: Icon, action }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 px-5 pt-5">
      <div className="flex min-w-0 items-start gap-3">
        {Icon && (
          <span className="mt-0.5 rounded-lg bg-accent-soft p-2 text-accent">
            <Icon className="h-4 w-4" aria-hidden />
          </span>
        )}
        <div className="min-w-0">
          <h2 className="text-[15px] font-semibold tracking-tight text-ink">{title}</h2>
          {subtitle && <p className="mt-0.5 text-sm text-ink-2">{subtitle}</p>}
        </div>
      </div>
      {action}
    </div>
  );
}

export function PageHeader({ eyebrow, title, children }) {
  return (
    <div className="mb-6 max-w-3xl">
      {eyebrow && <p className="mb-2 text-xs font-semibold uppercase tracking-[0.12em] text-accent">{eyebrow}</p>}
      <h1 className="text-2xl font-semibold tracking-tight text-ink sm:text-3xl">{title}</h1>
      {children && <p className="mt-2 text-[15px] leading-relaxed text-ink-2">{children}</p>}
    </div>
  );
}

const BADGE_TONES = {
  neutral: 'bg-raised text-ink-2 border-line',
  accent: 'bg-accent-soft text-accent border-transparent',
  good: 'bg-good-soft text-good border-transparent',
  warn: 'bg-warn-soft text-warn border-transparent',
  bad: 'bg-bad-soft text-bad border-transparent',
};

export function Badge({ tone = 'neutral', icon: Icon, className, children, ...props }) {
  return (
    <span
      className={cx(
        'inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2 py-0.5 text-xs font-medium',
        BADGE_TONES[tone],
        className,
      )}
      {...props}
    >
      {Icon && <Icon className="h-3 w-3" aria-hidden />}
      {children}
    </span>
  );
}

export function Button({ variant = 'primary', size = 'md', loading, icon: Icon, className, children, ...props }) {
  const variants = {
    primary: 'bg-accent text-accent-ink hover:brightness-110 shadow-sm',
    secondary: 'bg-surface text-ink border border-line hover:bg-raised',
    ghost: 'text-ink-2 hover:text-ink hover:bg-raised',
  };
  const sizes = { sm: 'h-8 px-3 text-xs gap-1.5', md: 'h-10 px-4 text-sm gap-2', lg: 'h-11 px-5 text-sm gap-2' };
  return (
    <button
      className={cx(
        'inline-flex cursor-pointer items-center justify-center rounded-xl font-medium transition disabled:cursor-not-allowed disabled:opacity-50',
        variants[variant],
        sizes[size],
        className,
      )}
      disabled={loading || props.disabled}
      {...props}
    >
      {loading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : Icon && <Icon className="h-4 w-4" aria-hidden />}
      {children}
    </button>
  );
}

/** Segmented control: options = [{value, label, hint?}] */
export function Segmented({ value, onChange, options, label, disabled, size = 'md' }) {
  return (
    <div role="radiogroup" aria-label={label} className={cx('inline-flex w-full rounded-xl border border-line bg-raised p-1', disabled && 'opacity-50')}>
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={active}
            title={opt.hint}
            disabled={disabled}
            onClick={() => onChange(opt.value)}
            className={cx(
              'flex-1 cursor-pointer whitespace-nowrap rounded-lg font-medium transition disabled:cursor-not-allowed',
              size === 'sm' ? 'px-2 py-1 text-xs' : 'px-3 py-1.5 text-[13px]',
              active ? 'bg-surface text-ink shadow-sm' : 'text-ink-2 hover:text-ink',
            )}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

export function Field({ label, hint, children }) {
  return (
    <label className="block">
      <span className="mb-1.5 flex items-baseline justify-between gap-2 text-xs font-medium text-ink-2">
        {label}
        {hint && <span className="font-normal text-ink-3">{hint}</span>}
      </span>
      {children}
    </label>
  );
}

export function Select({ value, onChange, children, className, ...props }) {
  return (
    <div className={cx('relative', className)}>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-10 w-full cursor-pointer appearance-none rounded-xl border border-line bg-surface pl-3 pr-9 text-sm text-ink transition hover:border-line-strong focus:border-accent focus:outline-none"
        {...props}
      >
        {children}
      </select>
      <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-3" aria-hidden />
    </div>
  );
}

const ALERT_TONES = {
  info: { cls: 'bg-accent-soft text-ink', icon: Info, iconCls: 'text-accent' },
  warn: { cls: 'bg-warn-soft text-ink', icon: AlertTriangle, iconCls: 'text-warn' },
  bad: { cls: 'bg-bad-soft text-ink', icon: XCircle, iconCls: 'text-bad' },
  good: { cls: 'bg-good-soft text-ink', icon: CheckCircle2, iconCls: 'text-good' },
};

export function Alert({ tone = 'info', title, children, className }) {
  const t = ALERT_TONES[tone];
  const Icon = t.icon;
  return (
    <div className={cx('flex gap-3 rounded-xl px-4 py-3 text-sm', t.cls, className)} role={tone === 'bad' ? 'alert' : 'status'}>
      <Icon className={cx('mt-0.5 h-4 w-4 shrink-0', t.iconCls)} aria-hidden />
      <div className="min-w-0">
        {title && <p className="font-medium">{title}</p>}
        {children && <div className={cx('text-ink-2', title && 'mt-0.5')}>{children}</div>}
      </div>
    </div>
  );
}

export function Kbd({ children }) {
  return <kbd className="rounded-md border border-line bg-raised px-1.5 py-0.5 font-mono text-[11px] text-ink-2">{children}</kbd>;
}

export function Code({ children }) {
  return <code className="break-all rounded-md bg-raised px-1.5 py-0.5 font-mono text-[12px] text-ink">{children}</code>;
}

export function Skeleton({ className }) {
  return <div className={cx('animate-pulse rounded-lg bg-raised', className)} />;
}
