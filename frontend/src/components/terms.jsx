import { Check, X } from 'lucide-react';
import { cx } from './ui';

function escapeRegExp(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/** Renders translated text with the glossary terms it uses underlined. */
export function HighlightedText({ text, terms = [], className, rtl }) {
  const used = [...new Set(terms.filter((t) => t.used).map((t) => t.glossary_term))].sort((a, b) => b.length - a.length);
  if (!text) return null;
  if (!used.length) {
    return (
      <p dir={rtl ? 'rtl' : 'auto'} className={className}>
        {text}
      </p>
    );
  }
  const parts = text.split(new RegExp(`(${used.map(escapeRegExp).join('|')})`, 'g'));
  return (
    <p dir={rtl ? 'rtl' : 'auto'} className={className}>
      {parts.map((part, i) =>
        used.includes(part) ? (
          <mark
            key={i}
            className="rounded-[4px] bg-good-soft px-0.5 text-inherit underline decoration-good decoration-2 underline-offset-[5px]"
            title="Glossary term"
          >
            {part}
          </mark>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </p>
  );
}

/** Chips: English term → formal glossary term, with a used / missing mark. */
export function TermChips({ terms = [], compact }) {
  if (!terms.length) return <p className="text-xs text-ink-3">No glossary terms in this sentence.</p>;
  return (
    <ul className="flex flex-wrap gap-1.5" aria-label="Glossary terms">
      {terms.map((t) => (
        <li
          key={t.english}
          className={cx(
            'inline-flex items-center gap-1.5 rounded-lg border px-2 py-1 text-xs',
            t.used ? 'border-transparent bg-good-soft text-ink' : 'border-transparent bg-bad-soft text-ink',
          )}
        >
          {t.used ? <Check className="h-3 w-3 text-good" aria-label="used" /> : <X className="h-3 w-3 text-bad" aria-label="missing" />}
          <span className="text-ink-2">{t.english}</span>
          {!compact && (
            <>
              <span className="text-ink-3" aria-hidden>
                →
              </span>
              <span className="font-indic font-medium">{t.glossary_term}</span>
            </>
          )}
        </li>
      ))}
    </ul>
  );
}

export function termScore(terms = []) {
  return { used: terms.filter((t) => t.used).length, total: terms.length };
}
