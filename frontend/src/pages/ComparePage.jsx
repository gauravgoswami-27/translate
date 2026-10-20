import { useRef, useState } from 'react';
import { Columns3, Play } from 'lucide-react';
import { api } from '../api/client';
import ApiOffline from '../components/ApiOffline';
import { HighlightedText, TermChips, termScore } from '../components/terms';
import { Badge, Button, Card, CardHeader, Field, PageHeader, Segmented, Skeleton } from '../components/ui';
import { TUNED } from '../lib/languages';

export const SYSTEMS = [
  { model: 'base', name: 'Base model', detail: 'IndicTrans2 dist-200M, no domain training', color: 'var(--series-1)' },
  { model: 'raw', name: 'Distilled, raw drafts', detail: 'Run 4: LoRA on the teacher’s translations', color: 'var(--series-2)' },
  { model: 'formal', name: 'Terminology-aware', detail: 'Run 6: LoRA on glossary-repaired translations', color: 'var(--series-3)' },
];

const EXAMPLES = [
  'Check the three phase supply and the earthing before switching on.',
  'Connect the live wire and the neutral wire to the main switch, then test the insulation with a megger.',
  'Measure the voltage across the capacitor with a voltmeter.',
];

export default function ComparePage() {
  const [text, setText] = useState(EXAMPLES[0]);
  const [targetLang, setTargetLang] = useState('hin_Deva');
  const [results, setResults] = useState({});
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);
  const runId = useRef(0);

  async function run() {
    if (!text.trim()) return;
    const id = ++runId.current;
    setRunning(true);
    setError(null);
    setResults({});
    // Sequential on purpose: each model is loaded on first use, and the API serialises requests per model.
    for (const sys of SYSTEMS) {
      try {
        const r = await api.translate({ text, targetLang, domain: 'electrician', model: sys.model, terminology: 'none' });
        if (id !== runId.current) return;
        setResults((prev) => ({ ...prev, [sys.model]: r }));
      } catch (e) {
        if (id === runId.current) setError(e);
        break;
      }
    }
    if (id === runId.current) setRunning(false);
  }

  return (
    <>
      <PageHeader eyebrow="Side by side" title="What terminology-aware training changes">
        The same sentence through three models, with terminology enforcement switched off, so you see what each model
        does by itself. The formal glossary terms each output uses are underlined.
      </PageHeader>

      <Card className="mb-5">
        <CardHeader icon={Columns3} title="Sentence" subtitle="Electrician content in one of the four tuned languages." />
        <div className="grid gap-4 p-5 md:grid-cols-[1fr_auto] md:items-end">
          <Field label="English">
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={2}
              aria-label="English sentence"
              className="w-full resize-y rounded-xl border border-line bg-canvas p-3 text-[15px] text-ink focus:border-accent focus:outline-none"
            />
          </Field>
          <div className="flex flex-col gap-3 md:w-80">
            <Field label="Language">
              <Segmented
                label="Language"
                size="sm"
                value={targetLang}
                onChange={setTargetLang}
                options={TUNED.map((l) => ({ value: l.code, label: l.name }))}
              />
            </Field>
            <Button icon={Play} loading={running} onClick={run} disabled={!text.trim()}>
              Compare models
            </Button>
          </div>
          <div className="flex flex-wrap gap-1.5 md:col-span-2">
            {EXAMPLES.map((e) => (
              <button
                key={e}
                onClick={() => setText(e)}
                className="cursor-pointer rounded-lg border border-line px-2.5 py-1 text-xs text-ink-2 transition hover:text-ink"
              >
                {e.length > 52 ? `${e.slice(0, 52)}…` : e}
              </button>
            ))}
          </div>
        </div>
      </Card>

      {error && (
        <div className="mb-5">
          <ApiOffline error={error} />
        </div>
      )}

      <div className="grid gap-5 md:grid-cols-3">
        {SYSTEMS.map((sys) => {
          const r = results[sys.model];
          const score = r ? termScore(r.glossary_terms) : null;
          const pending = running && !r;
          return (
            <Card key={sys.model} className="flex flex-col overflow-hidden">
              <div className="h-1" style={{ background: sys.color }} aria-hidden />
              <div className="flex flex-1 flex-col gap-4 p-5">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="flex items-center gap-2 text-[15px] font-semibold">
                      <span className="h-2.5 w-2.5 rounded-full" style={{ background: sys.color }} aria-hidden />
                      {sys.name}
                    </h3>
                    <p className="mt-0.5 text-xs text-ink-3">{sys.detail}</p>
                  </div>
                  {score && score.total > 0 && (
                    <Badge tone={score.used === score.total ? 'good' : score.used === 0 ? 'bad' : 'warn'}>
                      {score.used}/{score.total}
                    </Badge>
                  )}
                </div>
                <div className="min-h-[112px] rounded-xl border border-line bg-canvas p-3.5">
                  {pending && (
                    <div className="space-y-2.5">
                      <Skeleton className="h-4 w-11/12" />
                      <Skeleton className="h-4 w-3/4" />
                      <Skeleton className="h-4 w-1/2" />
                    </div>
                  )}
                  {r && (
                    <HighlightedText text={r.translated_text} terms={r.glossary_terms} className="font-indic text-[17px] leading-[1.85]" />
                  )}
                  {!r && !pending && <p className="text-sm text-ink-3">Press “Compare models”.</p>}
                </div>
                {r && <TermChips terms={r.glossary_terms} compact />}
                {r && <p className="mt-auto text-xs text-ink-3">{(r.latency_ms / 1000).toFixed(2)} s</p>}
              </div>
            </Card>
          );
        })}
      </div>
    </>
  );
}
