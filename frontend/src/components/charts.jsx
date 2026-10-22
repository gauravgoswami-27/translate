import { useEffect, useState } from 'react';
import { BarChart3, Table2 } from 'lucide-react';
import { Card, Segmented } from './ui';

/** Card with title, legend, and a chart/table toggle (table view = accessibility relief). */
export function ChartFrame({ title, subtitle, legend, table, children, badge }) {
  const [view, setView] = useState('chart');
  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3 px-5 pt-5">
        <div className="min-w-0">
          <h2 className="flex flex-wrap items-center gap-2 text-[15px] font-semibold tracking-tight">
            {title}
            {badge}
          </h2>
          {subtitle && <p className="mt-0.5 text-sm text-ink-2">{subtitle}</p>}
        </div>
        {table && (
          <div className="w-44">
            <Segmented
              label="View"
              size="sm"
              value={view}
              onChange={setView}
              options={[
                { value: 'chart', label: <span className="inline-flex items-center gap-1"><BarChart3 className="h-3.5 w-3.5" />Chart</span> },
                { value: 'table', label: <span className="inline-flex items-center gap-1"><Table2 className="h-3.5 w-3.5" />Table</span> },
              ]}
            />
          </div>
        )}
      </div>
      {legend && view === 'chart' && <div className="px-5 pt-3">{legend}</div>}
      <div className="p-5 pt-4">{view === 'chart' || !table ? children : table}</div>
    </Card>
  );
}

export function Legend({ items }) {
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1.5" aria-label="Legend">
      {items.map((it) => (
        <li key={it.label} className="inline-flex items-center gap-2 text-xs text-ink-2">
          <span className="h-2.5 w-2.5 rounded-[3px]" style={{ background: it.color }} aria-hidden />
          {it.label}
        </li>
      ))}
    </ul>
  );
}

/** Recharts tooltip in design-system colours; values stay in ink, the swatch carries identity. */
export function ChartTooltip({ active, payload, label, unit = '', labelFormatter }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="min-w-40 rounded-xl border border-line bg-surface px-3 py-2.5 text-xs shadow-card">
      <p className="mb-1.5 font-semibold text-ink">{labelFormatter ? labelFormatter(label) : label}</p>
      <ul className="space-y-1">
        {payload.map((p) => (
          <li key={p.dataKey} className="flex items-center justify-between gap-4">
            <span className="inline-flex items-center gap-2 text-ink-2">
              <span className="h-2 w-2 rounded-[2px]" style={{ background: p.color }} aria-hidden />
              {p.name}
            </span>
            <span className="font-medium tabular-nums text-ink">
              {p.value == null ? '–' : `${p.value}${unit}`}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function DataTable({ columns, rows, caption, minWidth = 480 }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-line">
      <table className="w-full border-collapse text-sm" style={{ minWidth }}>
        {caption && <caption className="sr-only">{caption}</caption>}
        <thead>
          <tr className="bg-raised text-left text-xs text-ink-2">
            {columns.map((c) => (
              <th key={c.key} scope="col" className={`px-3 py-2.5 font-medium ${c.align === 'right' ? 'text-right' : ''}`}>
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.key ?? i} className="border-t border-line">
              {columns.map((c) => (
                <td key={c.key} className={`px-3 py-2.5 ${c.align === 'right' ? 'text-right tabular-nums' : ''} ${c.className ?? ''}`}>
                  {c.render ? c.render(r) : r[c.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * Resolved values of CSS custom properties, refreshed when the theme class on <html>
 * changes. Needed because SVG presentation attributes (fill, stroke) that Recharts
 * writes do not resolve var(--x).
 */
export function useCssVars(names) {
  const read = () => {
    const style = getComputedStyle(document.documentElement);
    return Object.fromEntries(names.map((n) => [n, style.getPropertyValue(`--${n}`).trim()]));
  };
  const [vars, setVars] = useState(read);
  useEffect(() => {
    const observer = new MutationObserver(() => setVars(read()));
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
    return () => observer.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [names.join(',')]);
  return vars;
}

const CHROME_VARS = ['ink-3', 'axis', 'grid', 'raised'];

/** Axis/grid styling for Recharts in the current theme. */
export function useChartChrome() {
  const c = useCssVars(CHROME_VARS);
  return {
    axisProps: { tick: { fill: c['ink-3'], fontSize: 12 }, axisLine: { stroke: c.axis }, tickLine: false },
    gridStroke: c.grid,
    cursorFill: c.raised,
  };
}
