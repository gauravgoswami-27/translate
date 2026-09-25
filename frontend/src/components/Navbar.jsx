import React, { useEffect, useState } from 'react';
import { Languages, Activity, Cpu, Sparkles, BookOpen, BarChart3, ArrowRightLeft } from 'lucide-react';
import { checkHealth } from '../api/client';

export default function Navbar({ activeTab, setActiveTab }) {
  const [backendStatus, setBackendStatus] = useState('checking');

  useEffect(() => {
    async function verifyStatus() {
      const res = await checkHealth();
      if (res.status === 'ok') {
        setBackendStatus('online');
      } else {
        setBackendStatus('offline');
      }
    }
    verifyStatus();
    const interval = setInterval(verifyStatus, 15000);
    return () => clearInterval(interval);
  }, []);

  const navItems = [
    { id: 'translator', label: 'Translation Playground', icon: Languages },
    { id: 'comparison', label: 'Baseline vs Domain', icon: ArrowRightLeft },
    { id: 'dashboard', label: 'Evaluation Metrics', icon: BarChart3 },
    { id: 'lms-reader', label: 'NCVET Course Reader', icon: BookOpen },
  ];

  return (
    <header className="bg-slate-900/90 border-b border-slate-800 sticky top-0 z-50 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          
          {/* Logo & Title */}
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-gradient-to-tr from-blue-600 to-indigo-600 rounded-xl shadow-lg shadow-blue-500/20">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="font-bold text-lg text-white tracking-wide">IndicVocational</h1>
                <span className="text-xs bg-blue-500/20 text-blue-400 border border-blue-500/30 px-2 py-0.5 rounded-full font-medium">
                  NCVET / MSDE Engine
                </span>
              </div>
              <p className="text-xs text-slate-400">Technical Content Localization Engine for Vocational Trades</p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="hidden md:flex space-x-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-slate-800 text-blue-400 border border-slate-700 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>

          {/* Status Badge */}
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700 text-xs">
              <Cpu className="w-3.5 h-3.5 text-indigo-400" />
              <span className="text-slate-300 font-mono">RTX 3050 CUDA</span>
              <span className="text-slate-600">|</span>
              <div className="flex items-center space-x-1.5">
                <span className={`w-2 h-2 rounded-full ${backendStatus === 'online' ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
                <span className={`font-medium ${backendStatus === 'online' ? 'text-emerald-400' : 'text-amber-400'}`}>
                  {backendStatus === 'online' ? 'FastAPI Active' : 'Fallback Demo'}
                </span>
              </div>
            </div>
          </div>

        </div>
      </div>
      
      {/* Mobile nav */}
      <div className="md:hidden flex overflow-x-auto px-4 py-2 border-t border-slate-800/60 space-x-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap ${
                isActive ? 'bg-blue-600 text-white' : 'text-slate-400 hover:bg-slate-800'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>
    </header>
  );
}

