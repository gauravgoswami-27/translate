import React, { useState, useEffect } from 'react';
import { BookOpen, Globe, CheckCircle2, ChevronRight, ChevronLeft, Zap, FileText } from 'lucide-react';
import { translateText } from '../api/client';

const COURSE_SLIDES = [
  {
    id: 1,
    title: "Practical 01: Insulation Resistance Measurement",
    module: "Module 2: Electrical Testing & Measuring Instruments",
    englishText: "Inspect the insulation resistance of the motor winding with a megger before connecting the main AC supply.",
    diagramLabel: "Megger Connection Diagram (Fig 2.1)",
    safetyNote: "Ensure the main supply circuit breaker is switched off before placing test leads.",
  },
  {
    id: 2,
    title: "Practical 02: Control Panel Safety & Grounding",
    module: "Module 3: Domestic & Industrial Electrical Wiring",
    englishText: "Switch off the main supply before opening the control panel. Connect the neutral wire to the terminal block and verify earthing.",
    diagramLabel: "Control Panel & Terminal Block Layout (Fig 3.4)",
    safetyNote: "Wear safety shoes and safety gloves while working near live wires.",
  },
  {
    id: 3,
    title: "Practical 03: Transformer Load & Protection",
    module: "Module 4: AC Transformers & Circuit Breakers",
    englishText: "Inspect the circuit breaker rating before operating the electrical load. Check single phase and three phase voltage balance.",
    diagramLabel: "3-Phase Circuit Breaker Wiring (Fig 4.2)",
    safetyNote: "Verify fuse rating before turning on high voltage supply.",
  }
];

const LOCALES = [
  { code: 'en', name: 'English (Original Syllabus)' },
  { code: 'hin_Deva', name: 'Hindi (हिंदी)' },
  { code: 'gom_Deva', name: 'Konkani (कोंकणी)' },
  { code: 'mai_Deva', name: 'Maithili (मैथिली)' },
  { code: 'doi_Deva', name: 'Dogri (डोगरी)' },
];

export default function LMSReaderMock() {
  const [activeSlide, setActiveSlide] = useState(0);
  const [selectedLocale, setSelectedLocale] = useState('hin_Deva');
  const [translatedContent, setTranslatedContent] = useState(null);
  const [loading, setLoading] = useState(false);

  const slide = COURSE_SLIDES[activeSlide];

  useEffect(() => {
    async function localizeSlide() {
      if (selectedLocale === 'en') {
        setTranslatedContent(null);
        return;
      }
      setLoading(true);
      const [transText, transSafety] = await Promise.all([
        translateText({ text: slide.englishText, target_lang: selectedLocale, domain: 'electrician' }),
        translateText({ text: slide.safetyNote, target_lang: selectedLocale, domain: 'electrician' }),
      ]);
      setTranslatedContent({
        body: transText.translated_text,
        safety: transSafety.translated_text,
        model: transText.model_name_or_path,
      });
      setLoading(false);
    }
    localizeSlide();
  }, [activeSlide, selectedLocale]);

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      
      {/* Header */}
      <div className="bg-slate-800/60 p-6 rounded-2xl border border-slate-700/80 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <BookOpen className="w-5 h-5 text-indigo-400" />
            <h2 className="text-xl font-bold text-white">NCVET / MSDE E-Book Reader Demo</h2>
          </div>
          <p className="text-slate-300 text-sm mt-1">
            Simulated vocational ITI learning platform demonstrating on-demand localized course slides.
          </p>
        </div>

        {/* Locale Selector */}
        <div className="flex items-center space-x-2 bg-slate-900 p-1.5 rounded-xl border border-slate-700">
          <Globe className="w-4 h-4 text-blue-400 ml-2" />
          <select
            value={selectedLocale}
            onChange={(e) => setSelectedLocale(e.target.value)}
            className="bg-transparent text-slate-100 text-xs font-semibold focus:outline-none pr-2 cursor-pointer"
          >
            {LOCALES.map((loc) => (
              <option key={loc.code} value={loc.code} className="bg-slate-900 text-slate-100">
                {loc.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Slide Viewer Card */}
      <div className="bg-slate-800/40 border border-slate-700 rounded-2xl p-6 space-y-6">
        
        {/* Slide Navigation Header */}
        <div className="flex items-center justify-between border-b border-slate-700/80 pb-4">
          <div className="space-y-0.5">
            <span className="text-xs font-semibold text-blue-400 uppercase tracking-wider">{slide.module}</span>
            <h3 className="text-lg font-bold text-white">{slide.title}</h3>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => setActiveSlide((prev) => Math.max(0, prev - 1))}
              disabled={activeSlide === 0}
              className="p-2 bg-slate-800 hover:bg-slate-700 disabled:opacity-30 rounded-xl text-slate-300 transition-all cursor-pointer"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <span className="text-xs font-mono text-slate-400 px-2">
              {activeSlide + 1} / {COURSE_SLIDES.length}
            </span>
            <button
              onClick={() => setActiveSlide((prev) => Math.min(COURSE_SLIDES.length - 1, prev + 1))}
              disabled={activeSlide === COURSE_SLIDES.length - 1}
              className="p-2 bg-slate-800 hover:bg-slate-700 disabled:opacity-30 rounded-xl text-slate-300 transition-all cursor-pointer"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Slide Content Layout */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-6">
          
          {/* Main Content Area */}
          <div className="md:col-span-3 space-y-4">
            
            <div className="bg-slate-900/90 p-5 rounded-2xl border border-slate-700/80 space-y-3 min-h-[160px] flex flex-col justify-between">
              <div>
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">
                  Lesson Content ({selectedLocale === 'en' ? 'Original Syllabus' : selectedLocale}):
                </span>
                
                {loading ? (
                  <div className="py-6 text-center text-xs text-slate-400">
                    Localizing course text with fine-tuned model...
                  </div>
                ) : (
                  <p className="text-base text-slate-100 font-medium leading-relaxed">
                    {translatedContent ? translatedContent.body : slide.englishText}
                  </p>
                )}
              </div>

              {translatedContent && (
                <div className="flex items-center space-x-1.5 text-[11px] text-emerald-400 pt-2 border-t border-slate-800">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Localized with checkpoint: <strong className="font-mono">{translatedContent.model}</strong></span>
                </div>
              )}
            </div>

            {/* Safety Warning Note */}
            <div className="bg-amber-950/30 border border-amber-800/40 p-4 rounded-xl space-y-1">
              <span className="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5" /> Safety Instruction:
              </span>
              <p className="text-xs text-amber-200 font-medium">
                {translatedContent ? translatedContent.safety : slide.safetyNote}
              </p>
            </div>

          </div>

          {/* Diagram Preview Sidebar */}
          <div className="md:col-span-2 bg-slate-900/80 p-4 rounded-2xl border border-slate-700/80 flex flex-col justify-between space-y-4">
            <div className="space-y-2">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-blue-400" /> E-Book Diagram Reference
              </span>
              
              <div className="bg-slate-950 border border-slate-800 rounded-xl h-40 flex items-center justify-center text-center p-4">
                <div className="space-y-2">
                  <Zap className="w-8 h-8 text-blue-400 mx-auto opacity-70" />
                  <p className="text-xs text-slate-300 font-medium">{slide.diagramLabel}</p>
                </div>
              </div>
            </div>

            <div className="text-[11px] text-slate-400 text-center">
              Source: Official NCVET Electrician Qualification Pack
            </div>
          </div>

        </div>

      </div>

    </div>
  );
}

