import React from 'react';
import { Play, Pause, Square, ShieldCheck } from 'lucide-react';

export default function BotEngine() {
  const strategies = [
    { id: 1, name: 'Intraday Momentum', type: 'Trend Scalper', risk: 'Moderate', winRate: '54.0%', enabled: true },
    { id: 2, name: 'Mean Reversion', type: 'Statistical Arb', risk: 'Low Risk', winRate: '58.5%', enabled: true },
    { id: 3, name: 'Breakout Volume', type: 'Directional', risk: 'High Risk', winRate: '49.8%', enabled: false },
    { id: 4, name: 'RSI Scalper', type: 'Micro Scalp', risk: 'Moderate', winRate: '52.1%', enabled: false },
    { id: 5, name: 'Swing Follower', type: 'Trend Horizon', risk: 'Low Risk', winRate: '51.2%', enabled: true },
  ];

  return (
    <div className="space-y-6">
      {/* Bot Hero Matrix */}
      <div className="glass-panel rounded-2xl p-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-5">
          <div className="space-y-1.5">
            <div className="flex items-center space-x-3">
              <h2 className="text-lg font-extrabold text-white tracking-tight">Bot Engine Control Matrix</h2>
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-red-500/15 border border-red-500/40 text-red-400">
                STATUS: STOPPED
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/15 border border-amber-500/30 text-amber-300">
                PAPER RUNTIME
              </span>
            </div>
            <p className="text-xs text-slate-400 max-w-xl">
              Autonomous signal dispatch pipeline. Simulates intraday orders on simulated NSE ticks with zero live market exposure.
            </p>
          </div>

          {/* Action Triggers: 24K Gold Start, Dark Pause, Crimson Stop */}
          <div className="flex items-center space-x-3">
            <button className="flex items-center space-x-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-amber-400 to-amber-500 hover:from-amber-300 hover:to-amber-400 text-black text-xs font-black shadow-[0_0_25px_rgba(245,158,11,0.35)] transition-all transform hover:-translate-y-0.5">
              <Play size={14} fill="currentColor" />
              <span>START BOT</span>
            </button>
            <button className="flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-black hover:bg-[#141210] border border-white/[0.12] text-slate-200 text-xs font-semibold transition-all">
              <Pause size={14} />
              <span>PAUSE</span>
            </button>
            <button className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 border border-red-500 text-white text-xs font-black shadow-[0_0_22px_rgba(239,68,68,0.35)] transition-all transform hover:-translate-y-0.5">
              <Square size={12} fill="currentColor" />
              <span>STOP ALL</span>
            </button>
          </div>
        </div>

        {/* Telemetry */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 pt-6 border-t border-white/[0.08]">
          <div className="p-3.5 rounded-xl bg-black border border-amber-500/20">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Today's P&L</span>
            <div className="text-lg font-bold font-mono text-amber-300 mt-1">+₹0.00</div>
          </div>
          <div className="p-3.5 rounded-xl bg-black border border-white/[0.08]">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Active Signals</span>
            <div className="text-lg font-bold font-mono text-slate-200 mt-1">0</div>
          </div>
          <div className="p-3.5 rounded-xl bg-black border border-red-500/20">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Daily Stop Loss</span>
            <div className="text-lg font-bold font-mono text-red-400 mt-1">₹2,500.00</div>
          </div>
          <div className="p-3.5 rounded-xl bg-black border border-amber-500/20">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Safety Circuit</span>
            <div className="text-lg font-bold font-mono text-amber-400 mt-1 flex items-center gap-1.5">
              <ShieldCheck size={16} className="text-amber-400" />
              <span>ARMED</span>
            </div>
          </div>
        </div>
      </div>

      {/* Strategies List */}
      <div className="glass-panel rounded-2xl p-6 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
          <div className="flex items-center space-x-3">
            <span className="px-3 py-1 text-xs font-bold rounded-lg bg-amber-500/15 text-amber-300 border border-amber-500/30">
              Active Strategies (5)
            </span>
            <span className="px-3 py-1 text-xs font-medium text-slate-400 hover:text-white cursor-pointer transition-colors">
              Performance Attribution
            </span>
          </div>
          <span className="text-xs text-amber-500/80 font-mono">CORE: #ENG-611</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
          {strategies.map((strat) => (
            <div
              key={strat.id}
              className={`p-4 rounded-xl bg-black border ${
                strat.risk === 'High Risk' ? 'border-red-500/25 hover:border-red-500/40' : 'border-white/[0.08] hover:border-amber-500/30'
              } transition-all flex flex-col justify-between`}
            >
              <div className="space-y-2.5">
                <div className="flex items-start justify-between">
                  <div>
                    <h4 className="text-xs font-bold text-white">{strat.name}</h4>
                    <span className="text-[11px] text-slate-500">{strat.type}</span>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded-full text-[9px] font-bold ${
                      strat.risk === 'High Risk'
                        ? 'text-red-400 bg-red-500/10 border border-red-500/30'
                        : 'text-amber-400 bg-amber-500/10 border border-amber-500/30'
                    }`}
                  >
                    {strat.risk}
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Intraday quant signals executed on simulated ticks.
                </p>
              </div>
              <div className="pt-3 mt-3 border-t border-white/[0.08] flex items-center justify-between">
                <span className="text-slate-400 font-mono text-xs">Win: <strong className="text-white">{strat.winRate}</strong></span>
                <span
                  className={`px-2 py-0.5 rounded text-[9px] font-mono font-bold ${
                    strat.enabled
                      ? 'text-amber-400 bg-amber-500/10 border border-amber-500/30'
                      : 'text-slate-500 bg-white/[0.04] border border-white/[0.08]'
                  }`}
                >
                  {strat.enabled ? 'ENABLED' : 'DISABLED'}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
