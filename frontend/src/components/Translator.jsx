import React, { useState } from 'react';
import { Sparkles, ArrowRight, Zap, RefreshCw, Check, Copy, AlertTriangle, ShieldCheck } from 'lucide-react';
import { translateText } from '../api/client';

const TARGET_LANGUAGES = [
  { code: 'hin_Deva', name: 'Hindi (हिंदी)', region: 'Primary Demonstrated Target' },
  { code: 'gom_Deva', name: 'Konkani (कोंकणी)', region: 'Stretch Target (Goa/West)' },
  { code: 'mai_Deva', name: 'Maithili (मैथिली)', region: 'Stretch Target (Bihar/East)' },
  { code: 'doi_Deva', name: 'Dogri (डोगरी)', region: 'Stretch Target (J&K/North)' },
  { code: 'ben_Beng', name: 'Bengali (বাংলা)', region: 'Scheduled Language' },
  { code: 'guj_Gujr', name: 'Gujarati (ગુજરાતી)', region: 'Scheduled Language' },
  { code: 'mar_Deva', name: 'Marathi (मराठी)', region: 'Scheduled Language' },
  { code: 'tam_Taml', name: 'Tamil (தமிழ்)', region: 'Scheduled Language' },
  { code: 'tel_Telu', name: 'Telugu (తెలుగు)', region: 'Scheduled Language' },
];

const PRESETS = [
  "Check the insulation resistance with a megger.",
  "Switch off the main supply before opening the control panel.",
  "Connect the neutral wire to the terminal block.",
  "Inspect the circuit breaker rating before operating the electrical load.",
  "Demonstrate maintenance of AC/DC machines and voltage stabilizer.",
  "Wear safety shoes while working near live wires."
];

export default function Translator() {
  const [inputText, setInputText] = useState(PRESETS[0]);
  const [targetLang, setTargetLang] = useState('hin_Deva');
  const [domain, setDomain] = useState('electrician');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  async function handleTranslate() {
    if (!inputText.trim()) return;
    setLoading(true);
    setResult(null);
    const data = await translateText({ text: inputText, target_lang: targetLang, domain });
    setResult(data);
    setLoading(false);
  }

  function handleCopy() {
    if (!result?.translated_text) return;
    navigator.clipboard.writeText(result.translated_text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      
      {/* Banner */}
      <div className="bg-gradient-to-r from-blue-900/40 via-indigo-900/40 to-slate-900 p-6 rounded-2xl border border-blue-500/20">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <Zap className="w-5 h-5 text-amber-400 fill-amber-400" />
              Vocational Translation Playground
            </h2>
            <p className="text-slate-300 text-sm">
              Translate vocational & electrician technical content into Indic languages with domain-adapted neural machine translation.
            </p>
          </div>
          <span className="hidden sm:inline-flex items-center gap-1.5 bg-emerald-500/10 text-emerald-400 text-xs px-3 py-1 rounded-full border border-emerald-500/20 font-medium">
            <ShieldCheck className="w-3.5 h-3.5" /> PEFT LoRA Enabled
          </span>
        </div>
      </div>

      {/* Preset Quick Actions */}
      <div className="space-y-2">
        <label className="text-xs font-semibold uppercase text-slate-400 tracking-wider">
          Quick Vocational Sentence Presets:
        </label>
        <div className="flex flex-wrap gap-2">
          {PRESETS.map((preset, idx) => (
            <button
              key={idx}
              onClick={() => setInputText(preset)}
              className="text-xs bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white px-3 py-1.5 rounded-lg border border-slate-700/60 transition-all text-left"
            >
              "{preset}"
            </button>
          ))}
        </div>
      </div>

      {/* Main Control Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Input Card */}
        <div className="bg-slate-800/50 border border-slate-700/80 rounded-2xl p-5 space-y-4 flex flex-col justify-between">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">English Source Text</span>
              <span className="text-xs text-slate-500">{inputText.length} characters</span>
            </div>
            
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Enter technical or electrician text to translate..."
              rows={5}
              className="w-full bg-slate-900/90 border border-slate-700/80 rounded-xl p-3.5 text-slate-100 text-sm focus:outline-none focus:border-blue-500 transition-all resize-none"
            />
          </div>

          {/* Options & Action */}
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              
              {/* Target Language Dropdown */}
              <div>
                <label className="block text-xs text-slate-400 mb-1 font-medium">Target Indic Language</label>
                <select
                  value={targetLang}
                  onChange={(e) => setTargetLang(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 text-slate-200 text-xs rounded-xl p-2.5 focus:outline-none focus:border-blue-500 font-medium"
                >
                  {TARGET_LANGUAGES.map((lang) => (
                    <option key={lang.code} value={lang.code}>
                      {lang.name} — {lang.region}
                    </option>
                  ))}
                </select>
              </div>

              {/* Domain Mode Switcher */}
              <div>
                <label className="block text-xs text-slate-400 mb-1 font-medium">Translation Domain</label>
                <div className="grid grid-cols-2 p-1 bg-slate-900 rounded-xl border border-slate-700">
                  <button
                    onClick={() => setDomain('electrician')}
                    className={`py-1.5 rounded-lg text-xs font-medium transition-all ${
                      domain === 'electrician' ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    Electrician Domain
                  </button>
                  <button
                    onClick={() => setDomain('general')}
                    className={`py-1.5 rounded-lg text-xs font-medium transition-all ${
                      domain === 'general' ? 'bg-slate-700 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    Baseline NMT
                  </button>
                </div>
              </div>

            </div>

            <button
              onClick={handleTranslate}
              disabled={loading || !inputText.trim()}
              className="w-full py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:opacity-50 text-white font-semibold text-sm rounded-xl shadow-lg shadow-blue-500/20 flex items-center justify-center space-x-2 transition-all cursor-pointer"
            >
              {loading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Translating with GPU Model...</span>
                </>
              ) : (
                <>
                  <span>Translate Sentence</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>

        </div>

        {/* Output Card */}
        <div className="bg-slate-800/50 border border-slate-700/80 rounded-2xl p-5 flex flex-col justify-between space-y-4">
          
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Translated Output</span>
              {result && (
                <button
                  onClick={handleCopy}
                  className="text-xs text-slate-400 hover:text-white flex items-center space-x-1 bg-slate-700/50 px-2.5 py-1 rounded-md transition-all"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? 'Copied!' : 'Copy'}</span>
                </button>
              )}
            </div>

            <div className="bg-slate-900/90 border border-slate-700/80 rounded-xl p-4 min-h-[140px] flex items-center justify-center">
              {loading ? (
                <div className="text-center space-y-2">
                  <RefreshCw className="w-6 h-6 animate-spin text-blue-400 mx-auto" />
                  <p className="text-xs text-slate-400">Processing neural inference on RTX 3050 GPU...</p>
                </div>
              ) : result ? (
                <p className="text-lg font-medium text-white leading-relaxed text-center font-sans">
                  {result.translated_text}
                </p>
              ) : (
                <p className="text-xs text-slate-500 text-center">
                  Click <span className="text-blue-400 font-medium">Translate Sentence</span> to view Indic output.
                </p>
              )}
            </div>
          </div>

          {/* Model Metadata Footer */}
          {result && (
            <div className="space-y-2 bg-slate-900/60 p-3.5 rounded-xl border border-slate-700/60 text-xs">
              <div className="flex items-center justify-between text-slate-300">
                <span className="font-mono text-slate-400">Model Checkpoint:</span>
                <span className="font-mono text-indigo-400 bg-indigo-950/60 px-2 py-0.5 rounded border border-indigo-800/40">
                  {result.model_name_or_path}
                </span>
              </div>

              <div className="flex items-center justify-between text-slate-300">
                <span className="font-mono text-slate-400">Execution Latency:</span>
                <span className="font-mono text-emerald-400">{result.latencyMs} ms</span>
              </div>

              {result.warning && (
                <div className="flex items-start space-x-1.5 text-amber-400 text-[11px] pt-1 border-t border-slate-800">
                  <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                  <span>{result.warning}</span>
                </div>
              )}
            </div>
          )}

        </div>

      </div>

    </div>
  );
}

