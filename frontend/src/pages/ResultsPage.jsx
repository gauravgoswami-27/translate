import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { AlertTriangle, BookText, FlaskConical, Repeat, ShieldCheck, Target } from 'lucide-react';
import results from '../data/results.json';
import { ChartFrame, ChartTooltip, DataTable, Legend, useChartChrome, useCssVars } from '../components/charts';
import { Alert, Badge, Card, CardHeader, PageHeader } from '../components/ui';
import { langName } from '../lib/languages';

// Fixed colour slot per system (validated palette; never reassigned between charts).
const SYSTEMS = [
  { key: 'base', label: 'Base 200M', color: 'var(--series-1)' },
  { key: 'raw', label: 'Distilled, raw drafts', color: 'var(--series-2)' },
  { key: 'formal', label: 'Terminology-aware', color: 'var(--series-3)' },
  { key: 'teacher', label: 'Teacher 1B', color: 'var(--series-4)' },
];
const LANGS = results.domainLangs;
const score = (lang, system) => results.domain.find((d) => d.lang === lang && d.system === system);
const mean = (xs) => xs.reduce((a, b) => a + b, 0) / xs.length;
const fmt = (v, d = 1) => (v == null ? '–' : Number(v).toFixed(d));

const complianceRows = LANGS.map((lang) => ({
  lang,
  name: langName(lang),
  ...Object.fromEntries(SYSTEMS.map((s) => [s.key, score(lang, s.key)?.compliance ?? null])),
}));

const forgetting = results.in22
  .filter((r) => LANGS.includes(r.lang))
  .map((r) => ({ ...r, deltaFormal: r.formal != null ? r.formal - r.base : null }));
const maxForgetting = Math.max(...forgetting.map((r) => Math.abs(r.deltaFormal ?? 0)));

const tiles = [
  {
    icon: Target,
    value: `${fmt(mean(LANGS.map((l) => score(l, 'formal').compliance)))}%`,
    label: 'formal-term use, terminology-aware model',
    note: `vs ${fmt(mean(LANGS.map((l) => score(l, 'raw').compliance)))}% after plain distillation`,
  },
  {
    icon: ShieldCheck,
    value: `${fmt(mean(LANGS.map((l) => score(l, 'formal+hy')?.compliance ?? 0)))}%`,
    label: 'with hybrid enforcement',
    note: 'placeholder retry only where a term is missing',
  },
  {
    icon: FlaskConical,
    value: `±${fmt(maxForgetting, 1)}`,
    label: 'chrF++ change on general text',
    note: 'IN22-Gen: no catastrophic forgetting',
  },
  {
    icon: BookText,
    value: results.corpus.sentences.toLocaleString('en-IN'),
    label: 'English sentences from 9 NIMI books',
    note: `${results.corpus.train.toLocaleString('en-IN')} train · ${results.corpus.dev} dev · ${results.corpus.test} test`,
  },
];

function StatTile({ icon: Icon, value, label, note }) {
  return (
    <Card className="p-5">
      <Icon className="mb-3 h-4 w-4 text-accent" aria-hidden />
      <p className="text-3xl font-semibold tracking-tight text-ink">{value}</p>
      <p className="mt-1 text-sm text-ink-2">{label}</p>
      <p className="mt-2 text-xs text-ink-3">{note}</p>
    </Card>
  );
}

const unverified = (
  <Badge tone="warn" icon={AlertTriangle} title="References are the teacher's own drafts until the human post-edited test sets are ready">
    provisional
  </Badge>
);

// Inference-time modes were all measured on the run-5 model.
const MODES = [
  { key: 'formal_run5', label: 'Model only' },
  { key: 'formal_run5+hy', label: 'Hybrid' },
  { key: 'formal_run5+ph', label: 'Always placeholders' },
  { key: 'formal_run5+cd', label: 'Constrained decoding' },
];

const seedRows = LANGS.map((lang) => {
  const a = score(lang, 'formal');
  const b = score(lang, 'formal_s43');
  return { key: lang, name: langName(lang), a, b, dChrf: Math.abs(a.chrf - b.chrf), dComp: Math.abs(a.compliance - b.compliance) };
});

const caseRows = ['mai_Deva', 'gom_Deva'].map((lang) => {
  const pct = (system) => {
    const r = results.caseEndings.find((c) => c.lang === lang && c.system === system);
    return r && r.detached + r.attached ? (100 * r.detached) / (r.detached + r.attached) : null;
  };
  return { key: lang, name: langName(lang), run5: pct('formal_run5'), run6: pct('formal'), s43: pct('formal_s43') };
});

const SERIES_VARS = ['series-1', 'series-2', 'series-3', 'series-4'];
// Bars grow in once; skipped for reduced-motion users and in headless screenshot runs (?static).
const ANIMATE =
  !window.matchMedia('(prefers-reduced-motion: reduce)').matches && !new URLSearchParams(window.location.search).has('static');

export default function ResultsPage() {
  const { axisProps, gridStroke, cursorFill } = useChartChrome();
  const series = useCssVars(SERIES_VARS);
  const colorOf = (s) => series[s.color.slice(6, -1)]; // 'var(--series-1)' -> resolved hex

  return (
    <>
      <PageHeader eyebrow="Experiments" title="Results">
        English → Hindi, Konkani, Maithili, Dogri on a 200-sentence electrician test set per language, plus the IN22-Gen
        general benchmark. Terminology use is measured against the formal glossary and doesn’t depend on references.
      </PageHeader>

      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {tiles.map((t) => (
          <StatTile key={t.label} {...t} />
        ))}
      </div>

      <div className="space-y-6">
        <ChartFrame
          title="Formal glossary term use by language"
          subtitle="Share of glossary terms in the English source that the output renders with the formal term (%)."
          legend={<Legend items={SYSTEMS} />}
          table={
            <DataTable
              caption="Formal glossary term use (%)"
              columns={[{ key: 'name', label: 'Language' }, ...SYSTEMS.map((s) => ({ key: s.key, label: s.label, align: 'right', render: (r) => fmt(r[s.key]) }))]}
              rows={complianceRows}
            />
          }
        >
          <div className="h-80 w-full">
            <ResponsiveContainer>
              <BarChart data={complianceRows} barGap={2} barCategoryGap="22%" margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
                <CartesianGrid stroke={gridStroke} vertical={false} />
                <XAxis dataKey="name" {...axisProps} />
                <YAxis domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} {...axisProps} axisLine={false} unit="%" />
                <Tooltip cursor={{ fill: cursorFill }} content={<ChartTooltip unit="%" />} />
                {SYSTEMS.map((s) => (
                  <Bar key={s.key} dataKey={s.key} name={s.label} fill={colorOf(s)} radius={[4, 4, 0, 0]} maxBarSize={28} isAnimationActive={ANIMATE} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-3 text-xs text-ink-3">
            Plain distillation copies the teacher’s habits, e.g. चरण (“stage”) for <em>phase</em> and पृथ्वी (“planet”) for{' '}
            <em>earthing</em>. Repairing the training data with the glossary fixes it.
          </p>
        </ChartFrame>

        <Card>
          <CardHeader
            title={<span className="inline-flex flex-wrap items-center gap-2">Ways to enforce terminology {unverified}</span>}
            subtitle="Run-5 terminology-aware model with each inference mode: term use (%) · chrF++ against teacher drafts."
          />
          <div className="p-5 pt-4">
            <DataTable
              caption="Terminology enforcement modes"
              columns={[
                { key: 'name', label: 'Language' },
                ...MODES.map((m) => ({
                  key: m.key,
                  label: m.label,
                  align: 'right',
                  render: (r) => (
                    <span className="whitespace-nowrap">
                      <span className="font-medium text-ink">{fmt(r[m.key]?.compliance)}%</span>
                      <span className="text-ink-3"> · {fmt(r[m.key]?.chrf)}</span>
                    </span>
                  ),
                })),
              ]}
              rows={LANGS.map((lang) => ({ key: lang, name: langName(lang), ...Object.fromEntries(MODES.map((m) => [m.key, score(lang, m.key)])) }))}
            />
            <p className="mt-3 text-xs text-ink-3">
              Hybrid reaches full term use at almost no fluency cost. Forcing placeholders everywhere costs about 2 chrF++;
              constrained decoding damages the sentences (terms inserted mid-word or tacked on at the end).
            </p>
          </div>
        </Card>

        <Card>
          <CardHeader
            title={<span className="inline-flex flex-wrap items-center gap-2">Translation quality on the domain test set {unverified}</span>}
            subtitle="chrF++ and BLEU; Δ = paired-bootstrap mean difference vs base (1,000 samples)."
          />
          <div className="space-y-4 p-5 pt-4">
            <Alert tone="warn" title="Not final">
              These references are the teacher’s own translations, which use loanwords. That biases the score against the
              formal model, and the teacher scores ~99 by construction. Final numbers come from the human post-edited test sets.
            </Alert>
            <DataTable
              caption="Domain test set scores"
              columns={[
                { key: 'name', label: 'Language' },
                { key: 'system', label: 'System', render: (r) => SYSTEMS.find((s) => s.key === r.system)?.label },
                { key: 'chrf', label: 'chrF++', align: 'right', render: (r) => fmt(r.chrf, 2) },
                { key: 'bleu', label: 'BLEU', align: 'right', render: (r) => fmt(r.bleu, 2) },
                {
                  key: 'delta',
                  label: 'Δ vs base',
                  align: 'right',
                  render: (r) =>
                    r.deltaChrf == null ? (
                      <span className="text-ink-3">–</span>
                    ) : (
                      <span className={r.pValue < 0.05 ? (r.deltaChrf > 0 ? 'text-good' : 'text-bad') : 'text-ink-3'}>
                        {r.deltaChrf > 0 ? '+' : ''}
                        {fmt(r.deltaChrf, 2)}
                        {r.pValue < 0.05 ? ' *' : ''}
                      </span>
                    ),
                },
              ]}
              rows={LANGS.flatMap((lang) =>
                SYSTEMS.filter((s) => s.key !== 'teacher').map((s) => ({ key: `${lang}-${s.key}`, name: langName(lang), ...score(lang, s.key) })),
              )}
            />
            <p className="text-xs text-ink-3">* p &lt; 0.05 (paired bootstrap).</p>
          </div>
        </Card>

        <Card>
          <CardHeader
            icon={Repeat}
            title={<span className="inline-flex flex-wrap items-center gap-2">Robustness and ablations {unverified}</span>}
            subtitle="How much results move between training runs, whether one joint model costs Hindi anything, and the case-ending fix."
          />
          <div className="grid gap-6 p-5 pt-4 lg:grid-cols-3">
            <div className="space-y-2">
              <h3 className="text-sm font-medium">Seed 42 vs seed 43</h3>
              <DataTable
                caption="Seed variance"
                minWidth={0}
                columns={[
                  { key: 'name', label: 'Language' },
                  { key: 'chrf', label: 'chrF++', align: 'right', render: (r) => `${fmt(r.a.chrf, 2)} / ${fmt(r.b.chrf, 2)}` },
                  { key: 'dChrf', label: '|Δ|', align: 'right', render: (r) => fmt(r.dChrf, 2) },
                ]}
                rows={seedRows}
              />
              <p className="text-xs text-ink-3">
                Retraining with another seed moves chrF++ by up to {fmt(Math.max(...seedRows.map((r) => r.dChrf)), 1)}: smaller
                differences between runs aren’t meaningful.
              </p>
            </div>
            <div className="space-y-2">
              <h3 className="text-sm font-medium">Hindi: joint vs Hindi-only training</h3>
              <DataTable
                caption="Joint vs Hindi-only"
                minWidth={0}
                columns={[
                  { key: 'label', label: 'Model' },
                  { key: 'chrf', label: 'chrF++', align: 'right', render: (r) => fmt(r.chrf, 2) },
                  { key: 'compliance', label: 'Terms', align: 'right', render: (r) => `${fmt(r.compliance)}%` },
                ]}
                rows={[
                  { key: 'j', label: 'Joint (4 languages)', ...score('hin_Deva', 'formal') },
                  { key: 'h', label: 'Hindi only', ...score('hin_Deva', 'formal_hi') },
                ]}
              />
              <p className="text-xs text-ink-3">No measurable difference: one joint model serves all four languages without costing Hindi.</p>
            </div>
            <div className="space-y-2">
              <h3 className="text-sm font-medium">Detached case endings after terms</h3>
              <DataTable
                caption="Detached case endings"
                minWidth={0}
                columns={[
                  { key: 'name', label: 'Language' },
                  { key: 'run5', label: 'Run 5', align: 'right', render: (r) => `${fmt(r.run5)}%` },
                  { key: 'run6', label: 'Run 6', align: 'right', render: (r) => `${fmt(r.run6)}%` },
                ]}
                rows={caseRows}
              />
              <p className="text-xs text-ink-3">
                Placeholder repair had taught the run-5 model to write case endings as separate words (विद्युतरोधन क). Retraining
                on case-fixed data removed it.
              </p>
            </div>
          </div>
        </Card>

        <div className="grid gap-6 lg:grid-cols-5">
          <div className="lg:col-span-3">
            <ChartFrame
              title="IN22-Gen benchmark: base model, 22 languages"
              subtitle="chrF++ on 1,024 general-domain sentences per language (human references)."
              table={
                <DataTable
                  caption="IN22-Gen base model"
                  minWidth={0}
                  columns={[
                    { key: 'name', label: 'Language' },
                    { key: 'base', label: 'chrF++', align: 'right', render: (r) => fmt(r.base, 2) },
                    { key: 'baseBleu', label: 'BLEU', align: 'right', render: (r) => fmt(r.baseBleu, 2) },
                  ]}
                  rows={results.in22}
                />
              }
            >
              <div style={{ height: results.in22.length * 24 + 24 }} className="w-full">
                <ResponsiveContainer>
                  <BarChart data={results.in22} layout="vertical" margin={{ top: 0, right: 16, bottom: 0, left: 8 }} barCategoryGap={4}>
                    <CartesianGrid stroke={gridStroke} horizontal={false} />
                    <XAxis type="number" domain={[0, 80]} ticks={[0, 20, 40, 60, 80]} {...axisProps} />
                    <YAxis type="category" dataKey="name" width={78} {...axisProps} axisLine={false} interval={0} />
                    <Tooltip cursor={{ fill: cursorFill }} content={<ChartTooltip />} />
                    <Bar dataKey="base" name="chrF++" fill={series['series-1']} radius={[0, 4, 4, 0]} isAnimationActive={ANIMATE} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </ChartFrame>
          </div>
          <div className="space-y-6 lg:col-span-2">
            <Card>
              <CardHeader title="No forgetting" subtitle="IN22-Gen chrF++ for the four domain languages before and after domain training." />
              <div className="p-5 pt-4">
                <DataTable
                  caption="Forgetting check"
                  minWidth={0}
                  columns={[
                    { key: 'name', label: 'Language' },
                    { key: 'base', label: 'Base', align: 'right', render: (r) => fmt(r.base, 2) },
                    { key: 'formal', label: 'Term-aware', align: 'right', render: (r) => fmt(r.formal, 2) },
                    {
                      key: 'deltaFormal',
                      label: 'Δ',
                      align: 'right',
                      render: (r) => (
                        <span className="text-ink-2">
                          {r.deltaFormal > 0 ? '+' : ''}
                          {fmt(r.deltaFormal, 2)}
                        </span>
                      ),
                    },
                  ]}
                  rows={forgetting}
                />
              </div>
            </Card>
            <Card>
              <CardHeader title="Training-data repair" subtitle="Teacher drafts re-translated with glossary placeholders (run 5)." />
              <div className="p-5 pt-4">
                <DataTable
                  caption="Terminology repair statistics"
                  minWidth={0}
                  columns={[
                    { key: 'name', label: 'Language' },
                    { key: 'needed', label: 'Needed', align: 'right' },
                    { key: 'rate', label: 'Repaired', align: 'right' },
                  ]}
                  rows={LANGS.filter((l) => results.repair[l]).map((l) => {
                    const r = results.repair[l];
                    return { key: l, name: langName(l), needed: r.needed_repair.toLocaleString('en-IN'), rate: `${fmt((100 * r.repaired) / r.needed_repair)}%` };
                  })}
                />
              </div>
            </Card>
          </div>
        </div>

        <p className="text-xs text-ink-3">
          Data: {results.sources.domain}, {results.sources.in22}, {results.sources.repair}. Exported {results.generated} by{' '}
          <code className="font-mono">python -m backend.export_frontend_results</code>.
        </p>
      </div>
    </>
  );
}
