import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import HomePage from './components/SharedPages';
import ChartsPage from './components/ChartsPage';
import ScannerPage from './components/ScannerPage';
import PredictionsPage from './components/PredictionsPage';
import StrategiesPage from './components/StrategiesPage';

export default function App() {
  const [activeTab, setActiveTab] = useState('home');
  const [backendReady, setBackendReady] = useState(false);

  useEffect(() => {
    // Verify backend connection on mount
    async function checkBackend() {
      try {
        const res = await fetch('/api/health');
        if (res.ok) {
          setBackendReady(true);
        }
      } catch (e) {
        setBackendReady(false);
      }
    }
    checkBackend();
  }, []);

  return (
    <div className="min-h-screen bg-[#000000] text-[#F5F5F7] flex flex-col antialiased">
      {/* Header with mono design tokens */}
      <Header activeTab={activeTab} setActiveTab={setActiveTab} />

      {/* Main Viewport */}
      <main className="flex-1 w-full max-w-[1920px] mx-auto p-4 md:p-6 space-y-6">
        {activeTab === 'home' && <HomePage onNavigate={(tab) => setActiveTab(tab)} />}
        {activeTab === 'charts' && <ChartsPage />}
        {activeTab === 'scanner' && <ScannerPage />}
        {activeTab === 'predictions' && <PredictionsPage />}
        {activeTab === 'strategies' && <StrategiesPage />}
      </main>

      {/* Minimal Footer */}
      <footer className="border-t border-white/[0.08] bg-black px-6 py-3 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500">
        <div>ApexTrade v6.1.1 — Analysis & Prediction Only</div>
        <div className="font-mono text-[11px] text-slate-400">Paper Environment • Zero Real Funds at Risk</div>
      </footer>
    </div>
  );
}