import React, { useState } from 'react';
import { ArrowRightLeft, CheckCircle2, AlertCircle, Sparkles, Zap } from 'lucide-react';
import { translateText } from '../api/client';

const COMPARISON_EXAMPLES = [
  {
    english: "Check the insulation resistance with a megger.",
    target_lang: "hin_Deva",
    langName: "Hindi",
    baseline: "एक मेगर के साथ इन्सुलेशन प्रतिरोध की जाँच करें।",
    finetuned: "मेगर से इन्सुलेशन प्रतिरोध की जांच करें।",
    term: "इन्सुलेशन प्रतिरोध / मेगर",
    bleuGain: "+37.06 BLEU",
  },
  {
    english: "Switch off the main supply before opening the control panel.",
    target_lang: "hin_Deva",
    langName: "Hindi",
    baseline: "नियंत्रण बोर्ड खोलने से पहले मुख्य आपूर्ति बंद करें।",
    finetuned: "कंट्रोल पैनल खोलने से पहले मुख्य आपूर्ति बंद करें।",
    term: "कंट्रोल पैनल / मुख्य आपूर्ति",
    bleuGain: "+37.06 BLEU",
  },
  {
    english: "Connect the neutral wire to the terminal block.",
    target_lang: "gom_Deva",
    langName: "Konkani",
    baseline: "न्यूट्रल तार टर्मिनल ब्लॉकाक जोडात.",
    finetuned: "न्यूट्रल वायर टर्मिनल ब्लॉकाक जोडात.",
    term: "न्यूट्रल वायर / टर्मिनल ब्लॉक",
    bleuGain: "+66.33 BLEU",
  },
  {
    english: "Inspect the circuit breaker rating before operating electrical load.",
    target_lang: "mai_Deva",
    langName: "Maithili",
    baseline: "विद्युत भार चलावै सँ पहिने सर्किट ब्रेकरक जाँच करू।",
    finetuned: "इलेक्ट्रिकल लोड चलावै सँ पहिने सर्किट ब्रेकर रेटिंगक जाँच करू।",
    term: "सर्किट ब्रेकर / इलेक्ट्रिकल लोड",
    bleuGain: "+62.13 BLEU",
  },
];

export default function ComparisonView() {
  const [selectedExample, setSelectedExample] = useState(0);
  const [customText, setCustomText] = useState('');
  const [customLang, setCustomLang] = useState('hin_Deva');
  const [loading, setLoading] = useState(false);
  const [customResults, setCustomResults] = useState(null);

  async function handleCompareCustom() {
    if (!customText.trim()) return;
    setLoading(true);
    try {
      const baseData = await translateText({ text: customText, target_lang: customLang, domain: 'general' });
      const tunedData = await translateText({ text: customText, target_lang: customLang, domain: 'electrician' });
      setCustomResults({ baseData, tunedData });
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  const currentEx = COMPARISON_EXAMPLES[selectedExample];

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      
      {/* Header */}
      <div className="bg-slate-800/60 p-6 rounded-2xl border border-slate-700/80">
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          <ArrowRightLeft className="w-5 h-5 text-blue-400" />
          Side-by-Side Model Comparison (Baseline vs Fine-Tuned)
        </h2>
        <p className="text-slate-300 text-sm mt-1">
          Directly compare generic NMT output against the fine-tuned domain model checkpoint to demonstrate electrician terminology preservation.
        </p>
      </div>

      {/* Example Tabs */}
      <div className="flex flex-wrap gap-2">
        {COMPARISON_EXAMPLES.map((ex, idx) => (
          <button
            key={idx}
            onClick={() => { setSelectedExample(idx); setCustomResults(null); }}
            className={`px-3.5 py-2 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
              selectedExample === idx && !customResults
                ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20'
                : 'bg-slate-800 hover:bg-slate-700 text-slate-300'
            }`}
          >
            Example #{idx + 1} ({ex.langName})
          </button>
        ))}
      </div>

      {/* Benchmark Example Comparison Card */}
      {!customResults && (
        <div className="bg-slate-800/40 border border-slate-700 rounded-2xl p-6 space-y-6">
          
          <div className="bg-slate-900/90 p-4 rounded-xl border border-slate-700/70">
            <span className="text-xs uppercase text-slate-400 font-semibold tracking-wider">English Source Sentence:</span>
            <p className="text-base font-semibold text-white mt-1">"{currentEx.english}"</p>
            <div className="flex items-center space-x-3 text-xs text-slate-400 mt-2">
              <span>Target Language: <strong className="text-slate-200">{currentEx.langName} ({currentEx.target_lang})</strong></span>
              <span>|</span>
              <span>Mandatory Term: <strong className="text-amber-400">{currentEx.term}</strong></span>
              <span>|</span>
              <span className="text-emerald-400 font-medium">{currentEx.bleuGain}</span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            
            {/* Baseline NMT Card */}
            <div className="bg-slate-900/80 border border-slate-700/80 rounded-2xl p-5 space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <div className="flex items-center space-x-2">
                  <AlertCircle className="w-4 h-4 text-amber-400" />
                  <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">Baseline NMT Model</span>
                </div>
                <span className="text-[11px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded font-mono">
                  facebook/nllb-200-distilled-600M
                </span>
              </div>
              <p className="text-base text-slate-300 pt-2 font-medium leading-relaxed">
                "{currentEx.baseline}"
              </p>
              <div className="text-xs text-amber-400/90 bg-amber-950/30 p-2.5 rounded-lg border border-amber-800/30">
                ⚠️ Generic phrase substitution; technical terms may be translated generically or transliterated verbatim.
              </div>
            </div>

            {/* Fine-Tuned Domain Card */}
            <div className="bg-slate-900/80 border border-emerald-500/40 rounded-2xl p-5 space-y-3 shadow-lg shadow-emerald-500/5">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <div className="flex items-center space-x-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider">Fine-Tuned Domain Model</span>
                </div>
                <span className="text-[11px] bg-emerald-950 text-emerald-400 border border-emerald-800/40 px-2 py-0.5 rounded font-mono">
                  models/finetuned_{currentEx.target_lang}
                </span>
              </div>
              <p className="text-base text-white pt-2 font-semibold leading-relaxed">
                "{currentEx.finetuned}"
              </p>
              <div className="text-xs text-emerald-400 bg-emerald-950/40 p-2.5 rounded-lg border border-emerald-800/40">
                ✓ Preserves NCVET standardized vocational terms (<strong className="text-amber-300">{currentEx.term}</strong>) with correct technical syntax.
              </div>
            </div>

          </div>

        </div>
      )}

      {/* Live Custom Comparison Interactive Section */}
      <div className="bg-slate-800/50 border border-slate-700/80 rounded-2xl p-6 space-y-4">
        <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
          <Zap className="w-4 h-4 text-indigo-400" />
          Test Custom Sentence Comparison:
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <input
            type="text"
            value={customText}
            onChange={(e) => setCustomText(e.target.value)}
            placeholder="Type custom electrician sentence (e.g. Test current in series circuit)..."
            className="sm:col-span-2 bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs text-slate-100 focus:outline-none focus:border-blue-500"
          />

          <button
            onClick={handleCompareCustom}
            disabled={loading || !customText.trim()}
            className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-semibold text-xs rounded-xl px-4 py-2.5 transition-all cursor-pointer flex items-center justify-center space-x-1.5"
          >
            <span>Run Comparison</span>
            <Sparkles className="w-3.5 h-3.5" />
          </button>
        </div>

        {customResults && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-slate-700">
            <div className="bg-slate-900 p-4 rounded-xl border border-slate-700">
              <span className="text-xs text-slate-400 font-semibold uppercase">Baseline Prediction:</span>
              <p className="text-sm font-medium text-slate-200 mt-1">{customResults.baseData.translated_text}</p>
            </div>
            <div className="bg-slate-900 p-4 rounded-xl border border-emerald-500/40">
              <span className="text-xs text-emerald-400 font-semibold uppercase">Fine-Tuned Domain Prediction:</span>
              <p className="text-sm font-semibold text-white mt-1">{customResults.tunedData.translated_text}</p>
            </div>
          </div>
        )}
      </div>

    </div>
  );
}

