import { useEffect, useRef, useState } from 'react';
import { ArrowRight, Check, Clock, Copy, Cpu, Languages, RotateCcw, Sparkles, Wand2 } from 'lucide-react';
import { api } from '../api/client';
import ApiOffline from '../components/ApiOffline';
import { HighlightedText, TermChips, termScore } from '../components/terms';
import { Alert, Badge, Button, Card, CardHeader, Field, Kbd, PageHeader, Segmented, Select, Skeleton } from '../components/ui';
import { LANGUAGES, langByCode } from '../lib/languages';

const PRESETS = [
  'Check the three phase supply and the earthing before switching on.',
  'Connect the live wire and the neutral wire to the main switch.',
  'Measure the insulation resistance of the motor winding with a megger.',
  'Use a circuit breaker of the correct rating for the electrical load.',
  'Measure the voltage across the capacitor with a voltmeter.',
  'Wear safety shoes while working near live wires.',
];

const MODEL_OPTIONS = [
  { value: 'auto', label: 'Auto', hint: 'Electrician + tuned language → terminology-aware model; otherwise base' },
  { value: 'formal', label: 'Formal', hint: 'Run 5: LoRA distilled on terminology-repaired drafts' },
  { value: 'raw', label: 'Raw', hint: 'Run 4: LoRA distilled on raw teacher drafts' },
  { value: 'base', label: 'Base', hint: 'IndicTrans2 dist-200M, untouched' },
];

const TERMINOLOGY_OPTIONS = [
  { value: 'hybrid', label: 'Hybrid', hint: 'Re-translate with placeholders only if a glossary term is missing' },
  { value: 'none', label: 'Off', hint: 'Model output as is' },
  { value: 'placeholder', label: 'Force', hint: 'Always force glossary terms via placeholders (less fluent)' },
];

const MODEL_LABEL = { base: 'Base 200M', raw: 'LoRA · raw (run 4)', formal: 'LoRA · formal (run 5)' };

export default function TranslatePage() {
  const [text, setText] = useState(PRESETS[0]);
  const [targetLang, setTargetLang] = useState('hin_Deva');
  const [domain, setDomain] = useState('electrician');
  const [model, setModel] = useState('auto');
  const [terminology, setTerminology] = useState('hybrid');
  const [state, setState] = useState({ status: 'idle' });
  const [slow, setSlow] = useState(false);
  const [copied, setCopied] = useState(false);
  const abortRef = useRef(null);

  useEffect(() => () => abortRef.current?.abort(), []);

  async function translate() {
    if (!text.trim()) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setState({ status: 'loading' });
    setSlow(false);
    const slowTimer = setTimeout(() => setSlow(true), 6000);
    try {
      const result = await api.translate({ text, targetLang, domain, model, terminology }, controller.signal);
      setState({ status: 'done', result });
    } catch (error) {
      if (error.name !== 'AbortError') setState({ status: 'error', error });
    } finally {
      clearTimeout(slowTimer);
    }
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(state.result.translated_text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      /* clipboard unavailable */
    }
  }

  const lang = langByCode[targetLang];
  const result = state.status === 'done' ? state.result : null;
  const score = result ? termScore(result.glossary_terms) : null;

  return (
    <>
      <PageHeader eyebrow="Playground" title="Translate electrician training content">
        English → 22 Indian languages with IndicTrans2. For Hindi, Konkani, Maithili and Dogri, electrician text is routed
        to the terminology-aware model, which uses the formal technical glossary.
      </PageHeader>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card className="flex flex-col">
          <CardHeader icon={Languages} title="English source" subtitle="Paste a sentence or pick an example." />
          <div className="flex flex-1 flex-col gap-4 p-5">
            <div className="relative">
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) translate();
                }}
                rows={5}
                maxLength={5000}
                aria-label="English source text"
                placeholder="e.g. Check the earthing before switching on the supply."
                className="w-full resize-y rounded-xl border border-line bg-canvas p-3.5 text-[15px] leading-relaxed text-ink placeholder:text-ink-3 focus:border-accent focus:outline-none"
              />
              <span className="pointer-events-none absolute bottom-3 right-3 text-[11px] text-ink-3">{text.length}/5000</span>
            </div>

            <div className="flex flex-wrap gap-1.5" aria-label="Example sentences">
              {PRESETS.map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setText(p)}
                  className="max-w-full cursor-pointer truncate rounded-lg border border-line bg-surface px-2.5 py-1 text-left text-xs text-ink-2 transition hover:border-line-strong hover:text-ink"
                  title={p}
                >
                  {p.length > 44 ? `${p.slice(0, 44)}…` : p}
                </button>
              ))}
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Target language">
                <Select value={targetLang} onChange={setTargetLang} aria-label="Target language">
                  <optgroup label="Electrician-tuned">
                    {LANGUAGES.filter((l) => l.tuned).map((l) => (
                      <option key={l.code} value={l.code}>
                        {l.name} · {l.native}
                      </option>
                    ))}
                  </optgroup>
                  <optgroup label="Base model only">
                    {LANGUAGES.filter((l) => !l.tuned).map((l) => (
                      <option key={l.code} value={l.code}>
                        {l.name} · {l.native}
                      </option>
                    ))}
                  </optgroup>
                </Select>
              </Field>
              <Field label="Content domain">
                <Segmented
                  label="Content domain"
                  value={domain}
                  onChange={setDomain}
                  options={[
                    { value: 'electrician', label: 'Electrician' },
                    { value: 'general', label: 'General' },
                  ]}
                />
              </Field>
              <Field label="Model">
                <Segmented label="Model" size="sm" value={model} onChange={setModel} options={MODEL_OPTIONS} />
              </Field>
              <Field label="Terminology" hint={domain === 'general' ? 'electrician only' : undefined}>
                <Segmented
                  label="Terminology enforcement"
                  size="sm"
                  value={terminology}
                  onChange={setTerminology}
                  options={TERMINOLOGY_OPTIONS}
                  disabled={domain === 'general'}
                />
              </Field>
            </div>

            <div className="mt-auto flex flex-wrap items-center justify-between gap-3 pt-1">
              <span className="hidden text-xs text-ink-3 sm:inline">
                <Kbd>Ctrl</Kbd> + <Kbd>Enter</Kbd> to translate
              </span>
              <Button size="lg" icon={ArrowRight} loading={state.status === 'loading'} onClick={translate} disabled={!text.trim()} className="w-full sm:w-auto">
                {state.status === 'loading' ? 'Translating…' : 'Translate'}
              </Button>
            </div>
          </div>
        </Card>

        <Card className="flex flex-col">
          <CardHeader
            icon={Sparkles}
            title={`${lang?.name ?? targetLang} translation`}
            subtitle={lang?.tuned ? 'Glossary terms are underlined.' : 'This language uses the base model only.'}
            action={
              result && (
                <Button size="sm" variant="secondary" icon={copied ? Check : Copy} onClick={copy}>
                  {copied ? 'Copied' : 'Copy'}
                </Button>
              )
            }
          />
          <div className="flex flex-1 flex-col gap-4 p-5">
            <div className="min-h-[148px] rounded-xl border border-line bg-canvas p-4">
              {state.status === 'idle' && (
                <div className="grid h-full min-h-[116px] place-items-center text-center text-sm text-ink-3">
                  <p>
                    The translation appears here.
                    <br />
                    Type a sentence or pick an example.
                  </p>
                </div>
              )}
              {state.status === 'loading' && (
                <div className="space-y-3" aria-live="polite">
                  <Skeleton className="h-5 w-11/12" />
                  <Skeleton className="h-5 w-4/5" />
                  <Skeleton className="h-5 w-2/3" />
                  {slow && (
                    <p className="pt-1 text-xs text-ink-3">
                      Still working… the first request after starting the API loads the model, which can take a minute.
                    </p>
                  )}
                </div>
              )}
              {state.status === 'error' && <ApiOffline error={state.error} />}
              {result && (
                <HighlightedText
                  text={result.translated_text}
                  terms={result.glossary_terms}
                  rtl={lang?.rtl}
                  className="font-indic text-[19px] leading-[1.9] text-ink"
                />
              )}
            </div>

            {result && (
              <>
                {result.warning && <Alert tone="warn">{result.warning}</Alert>}
                <div>
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-3">Glossary terms</h3>
                    {score.total > 0 && (
                      <Badge tone={score.used === score.total ? 'good' : 'warn'}>
                        {score.used}/{score.total} formal terms used
                      </Badge>
                    )}
                  </div>
                  <TermChips terms={result.glossary_terms} />
                </div>
                <div className="mt-auto flex flex-wrap gap-2 border-t border-line pt-4">
                  <Badge icon={Cpu}>{MODEL_LABEL[result.model] ?? result.model}</Badge>
                  <Badge icon={Clock}>{(result.latency_ms / 1000).toFixed(2)} s</Badge>
                  {result.terminology !== 'none' && <Badge icon={Wand2}>terminology: {result.terminology}</Badge>}
                  {result.placeholder_retry && (
                    <Badge tone="accent" icon={RotateCcw} title="A glossary term was missing, so the sentence was re-translated with placeholders">
                      placeholder retry
                    </Badge>
                  )}
                  {result.backend === 'fallback' && <Badge tone="warn">glossary fallback, not a model</Badge>}
                </div>
              </>
            )}
          </div>
        </Card>
      </div>
    </>
  );
}
