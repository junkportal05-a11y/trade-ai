import React, { useState } from 'react';
import { Play, Trophy, Sparkles, BarChart3 } from 'lucide-react';

export default function BacktestEngine() {
  const [symbol, setSymbol] = useState('NIFTY 50');
  const [strategy, setStrategy] = useState('SuperTrend Quant (10, 3.0)');
  const [startDate, setStartDate] = useState('2024-01-01');
  const [endDate, setEndDate] = useState('2024-11-05');
  const [capital, setCapital] = useState('100000');
  const [stopATR, setStopATR] = useState('3.0');

  // Exact authentic leaderboard preserving real data
  const leaderboardData = [
    { rank: '#1', name: 'SuperTrend Quant (10, 3.0)', winRate: '51.2%', sharpe: '0.63', trades: 184, avgReturn: '800.38', score: '170.94', top: true },
    { rank: '#2', name: 'VWAP Institutional Pullback', winRate: '56.4%', sharpe: '0.61', trades: 212, avgReturn: '742.10', score: '164.20' },
    { rank: '#3', name: 'EMA Ribbon Scalper 5m', winRate: '48.9%', sharpe: '0.58', trades: 310, avgReturn: '680.50', score: '158.45' },
    { rank: '#4', name: 'Opening Range Breakout 15m', winRate: '53.0%', sharpe: '0.54', trades: 142, avgReturn: '610.25', score: '151.10' },
    { rank: '#5', name: 'Bollinger Band Squeeze Mean-Rev', winRate: '59.2%', sharpe: '0.52', trades: 96, avgReturn: '590.00', score: '147.80' },
    { rank: '#6', name: 'MACD Divergence Quant Engine', winRate: '47.5%', sharpe: '0.49', trades: 178, avgReturn: '520.15', score: '139.30' },
  ];

  const inputClass =
    'w-full glass-input rounded-xl px-3 py-2 text-xs text-slate-200 font-mono';

  return (
    <div className="space-y-4">
      {/* Backtest Parameters Matrix */}
      <div className="glass-panel rounded-2xl p-6 space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-white/[0.08]">
          <div>
            <h3 className="text-sm font-bold text-white tracking-tight flex items-center gap-2">
              <BarChart3 size={16} className="text-amber-400" />
              Quantitative Backtest Engine
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Historical execution simulator with realistic NSE slippage and transaction fee modeling.
            </p>
          </div>
          <span className="px-2.5 py-1 rounded-full text-[10px] font-mono text-amber-400 bg-amber-500/10 border border-amber-500/30">
            ENGINE: v6.1-CORE
          </span>
        </div>

        {/* 6-Field Input Grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5">
          <div className="space-y-1.5">
            <label className="text-[10px] font-bold text-amber-400/90 uppercase tracking-wider">Symbol</label>
            <input
              type="text"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              className={inputClass}
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-[10px] font-bold text-amber-400/90 uppercase tracking-wider">Strategy</label>
            <select
              value={strategy}
              onChange={(e) => setStrategy(e.target.value)}
              className={inputClass}
            >
              <option>SuperTrend Quant (10, 3.0)</option>
              <option>Mean Reversion (2.0 StdDev)</option>
              <option>Breakout Volume (15m ORB)</option>
              <option>RSI Scalper (14-period)</option>
              <option>VWAP Pullback Engine</option>
            </select>
          </div>

          <div className="space-y-1.5">
            <label className="text-[10px] font-bold text-amber-400/90 uppercase tracking-wider">Start Date</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className={inputClass}
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-[10px] font-bold text-amber-400/90 uppercase tracking-wider">End Date</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className={inputClass}
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-[10px] font-bold text-amber-400/90 uppercase tracking-wider">Capital (₹)</label>
            <input
              type="text"
              value={capital}
              onChange={(e) => setCapital(e.target.value)}
              className={inputClass}
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-[10px] font-bold text-amber-400/90 uppercase tracking-wider">Stop ATR Mult</label>
            <input
              type="text"
              value={stopATR}
              onChange={(e) => setStopATR(e.target.value)}
              className={inputClass}
            />
          </div>
        </div>

        {/* Action Triggers: 24K Gold Run, Gold Rim Tournament */}
        <div className="flex flex-wrap items-center gap-3 pt-1">
          <button
            type="button"
            className="flex items-center space-x-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-amber-400 to-amber-500 hover:from-amber-300 hover:to-amber-400 text-black text-xs font-black shadow-[0_0_22px_rgba(245,158,11,0.35)] transition-all transform hover:-translate-y-0.5"
          >
            <Play size={13} fill="currentColor" />
            <span>RUN BACKTEST</span>
          </button>

          <button
            type="button"
            className="flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-black hover:bg-[#141210] border border-amber-500/30 text-amber-300 text-xs font-bold transition-all"
          >
            <Sparkles size={13} className="text-amber-400" />
            <span>RUN 30-STRATEGY TOURNAMENT</span>
          </button>
        </div>
      </div>

      {/* 30-Strategy Leaderboard Panel */}
      <div className="glass-panel rounded-2xl p-6 space-y-3">
        <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
          <h4 className="text-xs font-bold text-white tracking-tight uppercase flex items-center gap-2">
            <Trophy size={16} className="text-amber-400" />
            30-Strategy Leaderboard
          </h4>
          <span className="text-[11px] text-amber-500/80 font-mono">BENCHMARK: NIFTY 50 TRI</span>
        </div>

        <div className="overflow-x-auto rounded-xl border border-white/[0.08]">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-white/[0.08] text-[10px] uppercase tracking-wider text-slate-400 bg-black">
                <th className="py-3 px-4 font-semibold">Rank</th>
                <th className="py-3 px-4 font-semibold">Strategy Name</th>
                <th className="py-3 px-4 font-semibold text-right">Win Rate</th>
                <th className="py-3 px-4 font-semibold text-right">Sharpe</th>
                <th className="py-3 px-4 font-semibold text-right">Trades</th>
                <th className="py-3 px-4 font-semibold text-right">Avg Return (₹)</th>
                <th className="py-3 px-4 font-semibold text-right">Score</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04] font-mono tabular-nums text-slate-300">
              {leaderboardData.map((row, idx) => (
                <tr
                  key={idx}
                  className={`transition-colors ${
                    row.top
                      ? 'bg-amber-500/[0.08] border-l-2 border-amber-400'
                      : 'hover:bg-white/[0.02]'
                  }`}
                >
                  <td className="py-3 px-4">
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] ${
                        row.top
                          ? 'font-black bg-amber-400 text-black shadow-[0_0_8px_#f59e0b]'
                          : 'bg-white/[0.05] text-slate-400 border border-white/[0.08]'
                      }`}
                    >
                      {row.rank}
                    </span>
                  </td>
                  <td
                    className={`py-3 px-4 font-sans flex items-center gap-2 ${
                      row.top ? 'font-bold text-white' : 'text-slate-200'
                    }`}
                  >
                    {row.name}
                    {row.top && (
                      <span className="px-1.5 py-0.2 rounded-full bg-red-500/20 text-red-400 border border-red-500/30 text-[9px] font-mono font-bold">
                        LEADER
                      </span>
                    )}
                  </td>
                  <td
                    className={`py-3 px-4 text-right ${
                      row.top ? 'text-amber-400 font-bold' : 'text-amber-400/90'
                    }`}
                  >
                    {row.winRate}
                  </td>
                  <td className="py-3 px-4 text-right">{row.sharpe}</td>
                  <td className="py-3 px-4 text-right text-slate-400">{row.trades}</td>
                  <td
                    className={`py-3 px-4 text-right ${
                      row.top ? 'text-amber-400 font-bold' : 'text-amber-400/90'
                    }`}
                  >
                    {row.avgReturn}
                  </td>
                  <td
                    className={`py-3 px-4 text-right ${
                      row.top ? 'font-black text-amber-300' : 'font-bold text-white'
                    }`}
                  >
                    {row.score}
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
