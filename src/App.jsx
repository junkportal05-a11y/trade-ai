import React, { useState } from 'react';
import Header from './components/Header';
import BotEngine from './components/BotEngine';
import TradeLog from './components/TradeLog';
import BacktestEngine from './components/BacktestEngine';
import {
  HomePage,
  TerminalPage,
  ScannerPage,
  PredictionsPage,
  AnalyticsPage,
  JournalPage,
  SecurityPage
} from './components/SharedPages';

export default function App() {
  const [activeTab, setActiveTab] = useState('bot');

  return (
    <div className="min-h-screen bg-[#050506] text-[#f8fafc] flex flex-col antialiased">
      {/* 3-Tier Zero-Collision Workstation Header */}
      <Header activeTab={activeTab} setActiveTab={setActiveTab} />

      {/* Main Workstation Viewport */}
      <main className="flex-1 w-full max-w-[1920px] mx-auto p-4 md:p-6 space-y-6">
        {activeTab === 'home' && <HomePage onNavigate={(tab) => setActiveTab(tab)} />}

        {activeTab === 'bot' && (
          <div className="space-y-6">
            <BotEngine />
            <TradeLog />
            <BacktestEngine />
          </div>
        )}

        {activeTab === 'terminal' && <TerminalPage />}
        {activeTab === 'scanner' && <ScannerPage />}
        {activeTab === 'predictions' && <PredictionsPage />}
        {activeTab === 'analytics' && <AnalyticsPage />}
        {activeTab === 'journal' && <JournalPage />}
        {activeTab === 'security' && <SecurityPage />}
      </main>

      {/* Minimal Footer */}
      <footer className="border-t border-white/[0.08] bg-black px-6 py-3 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500">
        <div>ApexTrade v6.1.1 — Owner-Only NSE Intraday Paper Signal System</div>
        <div className="font-mono text-[11px] text-amber-500/70">Simulated Environment • Zero Real Funds at Risk</div>
      </footer>
    </div>
  );
}
