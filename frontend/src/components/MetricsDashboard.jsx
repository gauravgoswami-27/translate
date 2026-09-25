import React from 'react';
import { BarChart3, TrendingUp, Award, Cpu, BookOpen, Layers } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line } from 'recharts';

const COMPARISON_DATA = [
  { language: 'Hindi (hin)', baselineBLEU: 11.24, tunedBLEU: 48.30, baselineChrf: 13.72, tunedChrf: 70.52 },
  { language: 'Konkani (gom)', baselineBLEU: 11.02, tunedBLEU: 77.35, baselineChrf: 22.66, tunedChrf: 83.67 },
  { language: 'Maithili (mai)', baselineBLEU: 11.88, tunedBLEU: 74.01, baselineChrf: 12.84, tunedChrf: 79.68 },
  { language: 'Dogri (doi)', baselineBLEU: 11.25, tunedBLEU: 76.21, baselineChrf: 23.11, tunedChrf: 83.97 },
];

const LOSS_DATA = [
  { epoch: 'Epoch 1', loss: 1.2402 },
  { epoch: 'Epoch 2', loss: 0.2930 },
  { epoch: 'Epoch 3', loss: 0.1722 },
  { epoch: 'Epoch 4', loss: 0.1222 },
  { epoch: 'Epoch 5', loss: 0.0924 },
];

const SCHEDULED_LANG_SUMMARY = [
  { code: 'hin_Deva', name: 'Hindi', bleu: 49.60, chrf: 76.60 },
  { code: 'mai_Deva', name: 'Maithili', bleu: 50.22, chrf: 77.92 },
  { code: 'doi_Deva', name: 'Dogri', bleu: 11.25, chrf: 23.11 },
  { code: 'gom_Deva', name: 'Konkani', bleu: 11.02, chrf: 22.66 },
  { code: 'tam_Taml', name: 'Tamil', bleu: 2.61, chrf: 5.85 },
  { code: 'brx_Deva', name: 'Bodo', bleu: 2.56, chrf: 11.23 },
  { code: 'mni_Mtei', name: 'Manipuri', bleu: 2.56, chrf: 11.23 },
  { code: 'sat_Olck', name: 'Santali', bleu: 2.56, chrf: 11.23 },
  { code: 'tel_Telu', name: 'Telugu', bleu: 1.43, chrf: 0.39 },
  { code: 'kan_Knda', name: 'Kannada', bleu: 1.43, chrf: 0.40 },
  { code: 'mar_Deva', name: 'Marathi', bleu: 1.43, chrf: 0.41 },
  { code: 'guj_Gujr', name: 'Gujarati', bleu: 1.42, chrf: 0.41 },
];

export default function MetricsDashboard() {
  return (
    <div className="max-w-6xl mx-auto space-y-6">
      
      {/* Title */}
      <div className="bg-slate-800/60 p-6 rounded-2xl border border-slate-700/80">
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-indigo-400" />
          Research Paper Quantitative Metrics & Evaluation
        </h2>
        <p className="text-slate-300 text-sm mt-1">
          Empirical evaluation results supporting the IEEE research paper manuscript, comparing baseline NMT vs LoRA fine-tuned domain models across 22 scheduled Indian languages.
        </p>
      </div>

      {/* Highlights Summary Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        <div className="bg-slate-800/50 border border-slate-700 p-5 rounded-2xl space-y-2">
          <div className="flex items-center justify-between text-blue-400">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Hindi BLEU Improvement</span>
            <TrendingUp className="w-5 h-5" />
          </div>
          <p className="text-3xl font-extrabold text-white">48.30</p>
          <span className="text-xs text-emerald-400 font-semibold">+37.06 BLEU vs Baseline (11.24)</span>
        </div>

        <div className="bg-slate-800/50 border border-slate-700 p-5 rounded-2xl space-y-2">
          <div className="flex items-center justify-between text-indigo-400">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Konkani Stretch Gain</span>
            <Award className="w-5 h-5" />
          </div>
          <p className="text-3xl font-extrabold text-white">77.35</p>
          <span className="text-xs text-emerald-400 font-semibold">+66.33 BLEU vs Baseline (11.02)</span>
        </div>

        <div className="bg-slate-800/50 border border-slate-700 p-5 rounded-2xl space-y-2">
          <div className="flex items-center justify-between text-emerald-400">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">LoRA Parameters</span>
            <Cpu className="w-5 h-5" />
          </div>
          <p className="text-3xl font-extrabold text-white">1.18 M</p>
          <span className="text-xs text-slate-400 font-medium">0.1914% of 616M Model Parameters</span>
        </div>

        <div className="bg-slate-800/50 border border-slate-700 p-5 rounded-2xl space-y-2">
          <div className="flex items-center justify-between text-amber-400">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Real Corpus Provenance</span>
            <BookOpen className="w-5 h-5" />
          </div>
          <p className="text-3xl font-extrabold text-white">300 Pairs</p>
          <span className="text-xs text-slate-400 font-medium">680+ PDF Pages (Bharat Skills / NIMI)</span>
        </div>

      </div>

      {/* Main Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* BLEU & chrF Comparison Chart */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-5 space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Layers className="w-4 h-4 text-blue-400" />
            BLEU Score Gain (Baseline vs Fine-Tuned Domain)
          </h3>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={COMPARISON_DATA}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="language" stroke="#94a3b8" fontSize={11} />
                <YAxis stroke="#94a3b8" fontSize={11} domain={[0, 90]} />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '12px' }} />
                <Legend />
                <Bar dataKey="baselineBLEU" name="Baseline BLEU" fill="#64748b" radius={[6, 6, 0, 0]} />
                <Bar dataKey="tunedBLEU" name="Fine-Tuned BLEU" fill="#3b82f6" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Training Loss Curve Chart */}
        <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-5 space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-emerald-400" />
            LoRA Fine-Tuning Loss Curve (RTX 3050 GPU)
          </h3>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={LOSS_DATA}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="epoch" stroke="#94a3b8" fontSize={11} />
                <YAxis stroke="#94a3b8" fontSize={11} domain={[0, 1.4]} />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '12px' }} />
                <Line type="monotone" dataKey="loss" name="Training Loss" stroke="#10b981" strokeWidth={3} dot={{ r: 5 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

      </div>

      {/* 22-Language Baseline Table 1 Section */}
      <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-5 space-y-4">
        <h3 className="text-sm font-bold text-white flex items-center justify-between">
          <span>Scheduled Indic Languages Baseline Evaluation (Table 1 Excerpt)</span>
          <span className="text-xs font-mono text-slate-400">SacreBLEU / chrF Metric Engine</span>
        </h3>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-900/90 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-700">
              <tr>
                <th className="p-3">Language</th>
                <th className="p-3">Code</th>
                <th className="p-3">Baseline BLEU</th>
                <th className="p-3">Baseline chrF</th>
                <th className="p-3">Domain Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {SCHEDULED_LANG_SUMMARY.map((row) => (
                <tr key={row.code} className="hover:bg-slate-800/40">
                  <td className="p-3 font-semibold text-white">{row.name}</td>
                  <td className="p-3 font-mono text-slate-400">{row.code}</td>
                  <td className="p-3 font-mono text-blue-400">{row.bleu.toFixed(2)}</td>
                  <td className="p-3 font-mono text-indigo-400">{row.chrf.toFixed(2)}</td>
                  <td className="p-3">
                    {['hin_Deva', 'gom_Deva', 'mai_Deva', 'doi_Deva'].includes(row.code) ? (
                      <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-md text-[11px] font-medium">
                        ✓ Fine-Tuned Checkpoint Ready
                      </span>
                    ) : (
                      <span className="bg-slate-800 text-slate-400 px-2 py-0.5 rounded-md text-[11px]">
                        Baseline Supported
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}

