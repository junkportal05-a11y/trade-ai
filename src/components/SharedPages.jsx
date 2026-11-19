import React from 'react';
import {
  LineChart,
  TrendingUp,
  PieChart,
  BookOpen,
  ShieldCheck,
  Layers,
  Activity,
  Microscope,
} from 'lucide-react';

// ============================================================
// 6.1 HOME DASHBOARD
// ============================================================

export function HomePage({ onNavigate }) {
  return (
    <div className="space-y-6">
      <div className="rounded-2xl p-6 bg-[#0c0a09] border border-white/[0.08]">
        <h2 className="text-xl font-bold text-white tracking-tight">ApexTrade Workstation</h2>
        <p className="text-slate-400 max-w-xl">
          AI-powered market analysis and prediction engine. Live scanner, trend analysis,
          and strategy backtesting — all paper-only, zero real-funds risk.
        </p>
      </div>

      {/* Quick Stats Section */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-2xl p-4 bg-[#050506] border border-white/[0.08]">
          <p className="text-xs text-slate-500 uppercase tracking-wider">Total Predictions</p>
          <p className="text-2xl font-bold text-white">0</p>
        </div>
        <div className="rounded-2xl p-4 bg-[#050506] border border-white/[0.08]">
          <p className="text-xs text-slate-500 uppercase tracking-winner">Win Rate</p>
          <p className="text-2xl font-bold text-white">0.0%</p>
        </div>
        <div className="rounded-2xl p-4 bg-[#050506] border border-white/[0.08]">
          <p className="text-xs text-slate-500 uppercase tracking-wider">Active Strategies</p>
          <p className="text-2xl font-bold text-white">5</p>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// 6.2 CHARTS PAGE
// ============================================================

export function ChartsPage() {
  return (
    <div className="p-6 bg-[#0c0a09] min-h-screen">
      <h2 className="text-2xl font-bold text-white mb-4">Charts</h2>
      <p className="text-slate-400">
        Chart visualization page — Lightweight Charts integration for NSE instruments.
        Placeholder: deploy charting canvas with AI scan overlay.
      </p>
    </div>
  );
}

// ============================================================
// 6.3 SCANNER PAGE
// ============================================================

export function ScannerPage() {
  return (
    <div className="p-6 bg-[#0c0a09] min-h-screen">
      <h2 className="text-2xl font-bold text-white mb-4">Scanner</h2>
      <p className="text-slate-400">
        Real-time signal scanner for NSE instruments. Run scans, view risk calculations,
        and see allocation suggestions — all paper-only analysis.
      </p>
      <div className="mt-6">
        <button className="btn-accent px-4 py-2">
          Run Scanner
        </button>
      </div>
    </div>
  );
}

// ============================================================
// 6.4 PREDICTIONS PAGE
// ============================================================

export function PredictionsPage() {
  return (
    <div className="p-6 bg-[#0c0a09] min-h-screen">
      <h2 className="text-2xl font-bold text-white mb-4">Predictions</h2>
      <p className="text-slate-400">
        AI prediction engine with tracking log. Record predictions, track resolution,
        and view historical accuracy — all synthetic data labeled as such.
      </p>
      <div className="mt-6">
        <button className="btn-accent px-4 py-2">
          Record Prediction
        </button>
        <button className="btn-accent ml-2 px-4 py-2">
          Resolve Predictions
        </button>
      </div>
    </div>
  );
}

// ============================================================
// 6.5 STRATEGIES PAGE
// ============================================================

export function StrategiesPage() {
  const strategyPresets = [
    { id: "intraday_momentum", name: "Intraday Momentum", desc: "EMA crossover + RSI + volume filter. 15m timeframe.", risk: "Moderate", hold: "15m-2h" },
    { id: "mean_reversion", name: "Mean Reversion", desc: "Bollinger Band squeeze + RSI extremes. 5m-15m timeframe.", risk: "Low", hold: "5m-30m" },
    { id: "breakout_volume", name: "Breakout Volume", desc: "High volume breakout + ADX trend filter. 15m-1h timeframe.", risk: "High", hold: "30m-4h" },
    { id: "scalper_rsi", name: "RSI Scalper", desc: "Fast RSI extremes + EMA alignment. 1m-5m timeframe.", risk: "High", hold: "1m-10m" },
    { id: "swing_trend", name: "Swing Trend Follower", desc: "Daily EMA trend + weekly MACD. 1h-1d timeframe.", risk: "Low", hold: "1d-2w" },
  ];

  return (
    <div className="p-6 bg-[#0c0a09] min-h-screen">
      <h2 className="text-2xl font-bold text-white mb-4">Strategies</h2>
      <p className="text-slate-400">
        Five paper-trading strategy engines with backtest capability and leaderboard.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
        {strategyPresets.map((s) => (
          <div
            key={s.id}
            className="rounded-2xl p-4 bg-[#050506] border border-white/[0.08]"
          >
            <h4 className="font-bold text-white mb-2">{s.name}</h4>
            <p className="text-slate-400 text-sm">{s.desc}</p>
            <p className="text-xs text-slate-500">
              Risk: {s.risk} • Hold: {s.hold}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}