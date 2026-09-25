import React, { useState } from 'react';
import Navbar from './components/Navbar';
import Translator from './components/Translator';
import ComparisonView from './components/ComparisonView';
import MetricsDashboard from './components/MetricsDashboard';
import LMSReaderMock from './components/LMSReaderMock';

export default function App() {
  const [activeTab, setActiveTab] = useState('translator');

  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100">
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'translator' && <Translator />}
        {activeTab === 'comparison' && <ComparisonView />}
        {activeTab === 'dashboard' && <MetricsDashboard />}
        {activeTab === 'lms-reader' && <LMSReaderMock />}
      </main>

      <footer className="bg-slate-900 border-t border-slate-800/80 py-6 text-center text-xs text-slate-500 space-y-1">
        <p className="font-medium text-slate-400">
          Vocational Content Localization Engine — NCVET / MSDE Vocational Demonstration Project
        </p>
        <p className="font-mono text-[11px]">
          AI4Bharat IndicTrans2 & Meta NLLB-200 | Parameter-Efficient PEFT LoRA Fine-Tuned on NVIDIA RTX 3050 GPU
        </p>
      </footer>
    </div>
  );
}

