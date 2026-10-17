import { useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import results from '../data/results.json';
import { Badge, Card, PageHeader, Segmented } from '../components/ui';
import { TUNED } from '../lib/languages';

const STATUS = {
  standard: { tone: 'good', label: 'standard', hint: 'Established NCERT / CSTT usage' },
  proposed: { tone: 'warn', label: 'proposed', hint: 'Awaiting review by native-speaker instructors' },
  loanword_kept: { tone: 'neutral', label: 'loanword kept', hint: 'No established native term in use' },
};

const ACRONYMS = { ac: 'AC', dc: 'DC' };
const displayTerm = (english) =>
  english
    .split(' ')
    .map((w, i) => ACRONYMS[w] ?? (i === 0 ? w[0].toUpperCase() + w.slice(1) : w))
    .join(' ');

export default function GlossaryPage() {
  const [lang, setLang] = useState('hin_Deva');
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('all');
  const entries = results.glossary[lang] ?? [];

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return entries.filter(
      (e) =>
        (status === 'all' || e.status === status) &&
        (!q || e.english.includes(q) || e.term.includes(query.trim()) || e.loanword.includes(query.trim())),
    );
  }, [entries, query, status]);

  const counts = entries.reduce((acc, e) => ({ ...acc, [e.status]: (acc[e.status] ?? 0) + 1 }), {});

  return (
    <>
      <PageHeader eyebrow="Terminology" title="Formal electrician glossary">
        The terms the models are trained and checked against: native technical vocabulary (NCERT / CSTT style). The
        English loanword it replaces is shown for comparison. Entries marked “proposed” are still being reviewed.
      </PageHeader>

      <Card className="mb-5 p-4">
        <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)_minmax(0,1fr)] md:items-center">
          <Segmented label="Language" size="sm" value={lang} onChange={setLang} options={TUNED.map((l) => ({ value: l.code, label: l.name }))} />
          <label className="relative block">
            <span className="sr-only">Search terms</span>
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-3" aria-hidden />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search English or Indic term…"
              className="h-9 w-full rounded-xl border border-line bg-canvas pl-9 pr-3 text-sm text-ink placeholder:text-ink-3 focus:border-accent focus:outline-none"
            />
          </label>
          <Segmented
            label="Status"
            size="sm"
            value={status}
            onChange={setStatus}
            options={[
              { value: 'all', label: `All ${entries.length}` },
              { value: 'standard', label: `Std ${counts.standard ?? 0}` },
              { value: 'proposed', label: `Prop ${counts.proposed ?? 0}` },
              { value: 'loanword_kept', label: `Loan ${counts.loanword_kept ?? 0}` },
            ]}
          />
        </div>
      </Card>

      {filtered.length === 0 ? (
        <Card className="p-10 text-center text-sm text-ink-3">No terms match “{query}”.</Card>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((e) => {
            const s = STATUS[e.status];
            return (
              <Card key={e.english} className="flex flex-col gap-3 p-4">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm font-medium text-ink-2">{displayTerm(e.english)}</p>
                  <Badge tone={s.tone} title={s.hint}>
                    {s.label}
                  </Badge>
                </div>
                <p className="font-indic text-xl font-medium leading-snug text-ink">{e.term}</p>
                <div className="mt-auto space-y-1 text-xs text-ink-3">
                  {e.variants.length > 0 && (
                    <p>
                      also accepted: <span className="font-indic text-ink-2">{e.variants.join(', ')}</span>
                    </p>
                  )}
                  {e.loanword !== e.term && !e.variants.includes(e.loanword) && (
                    <p>
                      replaces loanword: <span className="font-indic text-ink-2">{e.loanword}</span>
                    </p>
                  )}
                </div>
              </Card>
            );
          })}
        </div>
      )}
      <p className="mt-5 text-xs text-ink-3">Source: {results.sources.glossary} (register = formal).</p>
    </>
  );
}
