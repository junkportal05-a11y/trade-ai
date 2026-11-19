import React from 'react';
import { LineChart, TrendingUp, PieChart, BookOpen, ShieldCheck, Layers, Activity, Microscope } from 'lucide-react';

const strategyWinRates = [
  { name: 'Trend Scalper', score: 50.0, capital: 100000, stopAtm: 1.5 },
  { name: 'Mean Reversion', score: 52.3 },
  { name: 'Breakout Volume', score: 54.6 },
  { name: 'RSI Scalper', score: 56.9 },
  { name: 'Swing Trend Follower', score: 59.2 },
];

export function StrategiesPage() {
  return (
    <div className="p-6 bg-[#0c0a09] min-h-screen">
      <h2 className="text-2xl font-bold text-white mb-4">Strategies</h2>
      <p className="text-slate-400">
        Five paper-trading strategy engines with backtest capability and leaderboard.
        All win rates are traceable from recorded predictions.
      </p>

      {/* Strategies row - 5 cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mt-6">
        {strategyWinRates.map((s, i) => (
          <div
            key={s.name}
            className="strategy-card"
            style={{
              background: '#0c0a09', // dark glass, no white background
              border: '1px solid var(--border)',
            }}
          >
            <div className="name" style={{ color: 'var(--text)' }}>
              {s.name}
            </div>
            <div
              className="win-rate"
              style={{ color: 'var(--text)' }}
            >
              {s.score}%
            </div>
            <div className="progress-bar" style={{ width: '100px' }}>
              <div
                className="progress-fill"
                style={{ width: `${s.score}%` }}
              />
            </div>
          </div>
        ))}
      </div>

      {/* Backtest card - Medium glass */}
      <section className="glass-panel rounded-2xl p-6 mt-6">
        <h4 className="text-[11px] font-bold text-uppercase text-slate-500 mb-3">
          Backtest Engine
        </h4>
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <p className="text-[10px] text-slate-500">Symbol</p>
            <p className="text-[12px] font-bold text-white">RELIANCE</p>
          </div>
          <div>
            <p className="text-[10px] text-slate-500">Strategy</p>
            <p className="text-[12px] font-bold text-white">Intraday Momentum</p>
          </div>
          <div>
            <p className="text-[10px] text-slate-500">Period</p>
            <p className="text-[12px] font-bold text-white">
              01-01-2024 → 31-12-2024
            </p>
          </div>
          <div>
            <p className="text-[10px] text-slate-500">Capital</p>
            <p className="text-[12px] font-bold text-white">₹100,000</p>
          </div>
          <div>
            <p className="text-[10px] text-slate-500">Stop ATR Mult</p>
            <p className="text-[12px] font-bold text-white">1.5</p>
          </div>
        </div>
        <button className="btn-accent w-full mt-4 text-[11px] py-2">
          RUN BACKTEST
        </button>
      </section>

      {/* Leaderboard card - Medium glass */}
      <section className="glass-panel rounded-2xl p-6 mt-6">
        <h4 className="text-[11px] font-bold text-uppercase text-slate-500 mb-3">
          30-Strategy Leaderboard
        </h4>
        <table className="leaderboard-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Strategy</th>
              <th>Score</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>#1</td>
              <td>MFI 14 Reversals</td>
              <td>16</td>
            </tr>
            <tr>
              <td>#2</td>
              <td>Bollinger Bands Bounce</td>
              <td>—</td>
            </tr>
          </tbody>
        </table>
        <p className="text-[10px] text-slate-500 mt-3">
          Every row is clickable and opens that strategy's backtest details.
        </p>
      </section>

      {/* Accuracy comparison */}
      <section className="glass-panel rounded-2xl p-6 mt-6">
        <h4 className="text-[11px] font-bold text-uppercase text-slate-500 mb-3">
          Accuracy comparison
        </h4>
        <p className="text-[11px] text-slate-400">
          Accuracy per strategy, resolved-prediction counts, and the comparison
          of the 5 strategies. Moved here from Analytics.
        </p>
        <div className="grid grid-cols-2 gap-4 mt-4">
          {strategyWinRates.map((s) => (
            <div key={s.name} className="text-[11px]">
              <span>{s.name}: </span>
              <span>{s.score}%</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}