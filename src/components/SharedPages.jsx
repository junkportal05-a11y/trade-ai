import React from 'react';
import {
  LineChart,
  Layers,
  TrendingUp,
  PieChart,
  BookOpen,
  ShieldCheck
} from 'lucide-react';

export function HomePage({ onNavigate }) {
  return (
    <div className="space-y-4">
      {/* Hero Overview */}
      <div className="glass-panel rounded-2xl p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="space-y-1.5">
          <div className="flex items-center space-x-2">
            <span className="px-2 py-0.5 bg-amber-500/10 border border-amber-500/30 rounded text-[11px] font-mono text-amber-400 font-semibold">
              WORKSTATION DESK
            </span>
            <span className="text-xs text-slate-500">v6.1.1 Production Build</span>
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight">ApexTrade Executive Console</h2>
          <p className="text-xs text-slate-400 max-w-xl">
            Private, owner-operated paper signals workstation for the National Stock Exchange of India. All prices and executions are mathematically simulated.
          </p>
        </div>

        <div className="flex items-center space-x-2.5">
          <button
            onClick={() => onNavigate('bot')}
            className="px-4 py-2 bg-gradient-to-r from-amber-400 to-amber-500 hover:from-amber-300 hover:to-amber-400 text-black rounded-lg text-xs font-black shadow-[0_0_15px_rgba(245,158,11,0.3)] transition-all"
          >
            Open Bot Engine
          </button>
          <button
            onClick={() => onNavigate('terminal')}
            className="px-4 py-2 bg-black hover:bg-[#141210] border border-white/[0.12] text-slate-200 rounded-lg text-xs font-semibold transition-all"
          >
            Launch Terminal
          </button>
        </div>
      </div>

      {/* Snapshot Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="glass-panel rounded-2xl p-5 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Trading Mode</span>
            <span className="px-2 py-0.5 rounded text-[10px] bg-amber-500/10 text-amber-400 border border-amber-500/30 font-semibold font-mono">
              SIMULATED
            </span>
          </div>
          <div className="text-lg font-bold text-slate-100">Zero Risk Paper Sandbox</div>
          <p className="text-xs text-slate-400">
            Real broker APIs are disabled. Signal dispatches execute internally in local sandbox memory.
          </p>
        </div>

        <div className="glass-panel rounded-2xl p-5 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Active Engine</span>
            <span className="px-2 py-0.5 rounded-full text-[10px] bg-red-500/10 text-red-400 border border-red-500/40 font-bold font-mono">
              STOPPED
            </span>
          </div>
          <div className="text-lg font-bold text-slate-100">SuperTrend Quant v10</div>
          <p className="text-xs text-slate-400">
            Ranked <span className="text-amber-400 font-bold">#1</span> in tournament backtests with <span className="text-amber-400 font-bold">51.2%</span> win rate and <span className="text-amber-300 font-bold">170.94</span> score.
          </p>
        </div>

        <div className="glass-panel rounded-2xl p-5 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">System State</span>
            <span className="px-2 py-0.5 rounded text-[10px] bg-amber-500/10 text-amber-400 border border-amber-500/30 font-semibold font-mono">
              SECURE
            </span>
          </div>
          <div className="text-lg font-bold text-slate-100">Single-Owner Session</div>
          <p className="text-xs text-slate-400">
            Zero external user endpoints exposed. Local source of truth active.
          </p>
        </div>
      </div>
    </div>
  );
}

export function TerminalPage() {
  return (
    <div className="glass-panel rounded-2xl p-6 space-y-4">
      <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
        <div className="flex items-center space-x-2">
          <LineChart size={16} className="text-amber-400" />
          <h3 className="text-sm font-bold text-white">NSE Terminal — Real-Time Tick Monitor</h3>
          <span className="text-[10px] bg-black border border-white/[0.1] text-slate-400 px-1.5 py-0.2 rounded font-mono">
            FEED: SIMULATED
          </span>
        </div>
        <span className="text-xs font-mono text-slate-500">TIMEFRAME: 5 MIN</span>
      </div>
      <div className="h-96 rounded-xl bg-black border border-white/[0.08] flex flex-col items-center justify-center space-y-2">
        <LineChart size={28} className="text-amber-500/60" />
        <span className="text-xs font-medium text-slate-400">High-Fidelity Multi-Timeframe Canvas</span>
        <span className="text-[11px] text-slate-600 font-mono">NIFTY 50 | <span className="text-amber-400">24,180.20</span> | CANDLESTICK ENGINE ARMED</span>
      </div>
    </div>
  );
}

export function ScannerPage() {
  return (
    <div className="glass-panel rounded-2xl p-6 space-y-4">
      <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
        <div className="flex items-center space-x-2">
          <Layers size={16} className="text-amber-400" />
          <h3 className="text-sm font-bold text-white">NSE Stock Scanner (Nifty 50 Universe)</h3>
        </div>
        <span className="text-xs text-slate-500 font-mono">INTERVAL: 1 MIN SCAN</span>
      </div>
      <div className="p-8 text-center text-slate-500 text-xs">
        Scanner running in memory. Filter criteria: Volume &gt; 1.5x 20-EMA, RSI &lt; 30 or &gt; 70.
      </div>
    </div>
  );
}

export function PredictionsPage() {
  return (
    <div className="glass-panel rounded-2xl p-6 space-y-4">
      <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
        <div className="flex items-center space-x-2">
          <TrendingUp size={16} className="text-amber-400" />
          <h3 className="text-sm font-bold text-white">Algorithmic Trend Forecaster</h3>
        </div>
        <span className="text-xs text-slate-500 font-mono">MODEL: PROBABILISTIC ATR</span>
      </div>
      <div className="p-8 text-center text-slate-500 text-xs">
        Signal confidence models ready. No open predictions while Bot Engine is stopped.
      </div>
    </div>
  );
}

export function AnalyticsPage() {
  return (
    <div className="glass-panel rounded-2xl p-6 space-y-4">
      <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
        <div className="flex items-center space-x-2">
          <PieChart size={16} className="text-amber-400" />
          <h3 className="text-sm font-bold text-white">Quantitative Portfolio Analytics</h3>
        </div>
        <span className="text-xs text-slate-500 font-mono">BASE CURRENCY: INR (₹)</span>
      </div>
      <div className="p-8 text-center text-slate-500 text-xs">
        Cumulative P&L, Sharpe Ratio, and Drawdown curves are initialized to zero.
      </div>
    </div>
  );
}

export function JournalPage() {
  return (
    <div className="glass-panel rounded-2xl p-6 space-y-4">
      <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
        <div className="flex items-center space-x-2">
          <BookOpen size={16} className="text-amber-400" />
          <h3 className="text-sm font-bold text-white">Intraday Trading Journal & Notes</h3>
        </div>
        <span className="text-xs text-slate-500 font-mono">LOCAL STORE ONLY</span>
      </div>
      <div className="p-8 text-center text-slate-500 text-xs">
        No journal entries logged for today.
      </div>
    </div>
  );
}

export function SecurityPage() {
  return (
    <div className="glass-panel rounded-2xl p-6 space-y-4">
      <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
        <div className="flex items-center space-x-2">
          <ShieldCheck size={16} className="text-amber-400" />
          <h3 className="text-sm font-bold text-white">System Security & Access Controls</h3>
        </div>
        <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-amber-500/10 border border-amber-500/30 text-amber-400">
          OWNER RESTRICTED
        </span>
      </div>
      <div className="space-y-3 text-xs text-slate-400">
        <div className="p-3 bg-black rounded-xl border border-white/[0.08] flex items-center justify-between">
          <span>Broker API Gateways</span>
          <span className="text-red-400 font-mono">DISCONNECTED (PAPER ONLY)</span>
        </div>
        <div className="p-3 bg-black rounded-xl border border-white/[0.08] flex items-center justify-between">
          <span>Multi-User Authentication</span>
          <span className="text-slate-500 font-mono">DISABLED (OWNER MONOLITH)</span>
        </div>
        <div className="p-3 bg-black rounded-xl border border-white/[0.08] flex items-center justify-between">
          <span>Local Storage Persistence</span>
          <span className="text-amber-400 font-mono">SYNCHRONIZED</span>
        </div>
      </div>
    </div>
  );
}
