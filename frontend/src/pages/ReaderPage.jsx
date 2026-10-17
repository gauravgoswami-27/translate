import { useEffect, useRef, useState } from 'react';
import { BookOpen, ChevronLeft, ChevronRight, HardHat, Languages } from 'lucide-react';
import { api } from '../api/client';
import ApiOffline from '../components/ApiOffline';
import { HighlightedText } from '../components/terms';
import { Badge, Button, Card, PageHeader, Segmented, Skeleton } from '../components/ui';
import { TUNED } from '../lib/languages';

// Sample lessons written for this demo in the style of the NIMI Electrician trade books.
const LESSONS = [
  {
    module: 'Testing & measuring instruments',
    title: 'Measuring insulation resistance',
    body: [
      'Switch off the main supply and disconnect the motor from the control panel.',
      'Measure the insulation resistance of the motor winding with a megger.',
      'Record the reading and compare it with the value given by the manufacturer.',
    ],
    safety: 'Never test a circuit with a megger while the live wire is connected to the supply.',
  },
  {
    module: 'Domestic wiring',
    title: 'Earthing a distribution board',
    body: [
      'Connect the earth wire of every circuit to the earthing terminal of the board.',
      'Connect the neutral wire to the neutral link and the live wire through the fuse.',
      'Check the earthing with an earth tester before switching on the supply.',
    ],
    safety: 'Wear safety shoes and use insulated tools while working near the switch board.',
  },
  {
    module: 'Three phase supply',
    title: 'Checking a three phase motor circuit',
    body: [
      'Check the voltage between each pair of lines of the three phase supply with a voltmeter.',
      'Select a circuit breaker of the correct rating for the electrical load.',
      'Connect the capacitor only after the supply has been switched off.',
    ],
    safety: 'Discharge the capacitor before touching its terminals.',
  },
];

export default function ReaderPage() {
  const [index, setIndex] = useState(0);
  const [lang, setLang] = useState('hin_Deva');
  const [showOriginal, setShowOriginal] = useState(true);
  const [state, setState] = useState({ status: 'loading' });
  const abortRef = useRef(null);
  const lesson = LESSONS[index];

  useEffect(() => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setState({ status: 'loading' });
    api
      .translateBatch({ texts: [...lesson.body, lesson.safety], targetLang: lang, domain: 'electrician' }, controller.signal)
      .then((res) => setState({ status: 'done', results: res.results }))
      .catch((error) => error.name !== 'AbortError' && setState({ status: 'error', error }));
    return () => controller.abort();
  }, [index, lang, lesson]);

  const translated = state.status === 'done' ? state.results : null;

  return (
    <>
      <PageHeader eyebrow="Integration demo" title="Course reader">
        How an LMS lesson could be shown in the trainee’s language, translated on demand through the API (electrician
        domain, hybrid terminology). Sample lessons written in the style of the NIMI trade books.
      </PageHeader>

      <Card className="mb-5 p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="w-full sm:max-w-md">
            <Segmented label="Language" size="sm" value={lang} onChange={setLang} options={TUNED.map((l) => ({ value: l.code, label: l.name }))} />
          </div>
          <label className="inline-flex cursor-pointer items-center gap-2 text-sm text-ink-2">
            <input type="checkbox" checked={showOriginal} onChange={(e) => setShowOriginal(e.target.checked)} className="h-4 w-4 accent-[var(--accent)]" />
            Show English alongside
          </label>
        </div>
      </Card>

      <Card className="overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-4">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-wider text-accent">
              Lesson {index + 1} of {LESSONS.length} · {lesson.module}
            </p>
            <h2 className="mt-0.5 text-lg font-semibold tracking-tight">{lesson.title}</h2>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="secondary" size="sm" icon={ChevronLeft} disabled={index === 0} onClick={() => setIndex((i) => i - 1)} aria-label="Previous lesson">
              <span className="hidden sm:inline">Previous</span>
            </Button>
            <Button variant="secondary" size="sm" disabled={index === LESSONS.length - 1} onClick={() => setIndex((i) => i + 1)} aria-label="Next lesson">
              <span className="hidden sm:inline">Next</span>
              <ChevronRight className="h-4 w-4" aria-hidden />
            </Button>
          </div>
        </div>

        <div className="p-5">
          {state.status === 'error' ? (
            <ApiOffline error={state.error} />
          ) : (
            <ol className="space-y-4">
              {lesson.body.map((sentence, i) => (
                <li key={sentence} className={`grid gap-2 ${showOriginal ? 'md:grid-cols-2 md:gap-6' : ''}`}>
                  <div className="flex gap-3">
                    <span className="mt-1 grid h-6 w-6 shrink-0 place-items-center rounded-full bg-accent-soft text-xs font-semibold text-accent">{i + 1}</span>
                    {translated ? (
                      <HighlightedText text={translated[i].translated_text} terms={translated[i].glossary_terms} className="font-indic text-[17px] leading-[1.85]" />
                    ) : (
                      <div className="w-full space-y-2 pt-1">
                        <Skeleton className="h-4 w-11/12" />
                        <Skeleton className="h-4 w-2/3" />
                      </div>
                    )}
                  </div>
                  {showOriginal && <p className="pl-9 text-sm leading-relaxed text-ink-3 md:pl-0 md:pt-1">{sentence}</p>}
                </li>
              ))}
            </ol>
          )}

          <div className="mt-6 flex gap-3 rounded-xl bg-warn-soft p-4">
            <HardHat className="mt-0.5 h-5 w-5 shrink-0 text-warn" aria-hidden />
            <div className="min-w-0 space-y-1">
              <p className="text-xs font-semibold uppercase tracking-wider text-warn">Safety</p>
              {translated ? (
                <HighlightedText
                  text={translated[lesson.body.length].translated_text}
                  terms={translated[lesson.body.length].glossary_terms}
                  className="font-indic text-[16px] leading-[1.8] text-ink"
                />
              ) : state.status === 'loading' ? (
                <Skeleton className="h-4 w-3/4" />
              ) : null}
              {showOriginal && <p className="text-sm text-ink-3">{lesson.safety}</p>}
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 border-t border-line px-5 py-3 text-xs text-ink-3">
          <BookOpen className="h-3.5 w-3.5" aria-hidden />
          Translated on demand
          {translated && (
            <>
              <Badge icon={Languages}>{translated[0].model === 'formal' ? 'terminology-aware model' : translated[0].model}</Badge>
              <span>{(translated[0].latency_ms / 1000).toFixed(1)} s for {translated.length} sentences</span>
            </>
          )}
        </div>
      </Card>
    </>
  );
}
