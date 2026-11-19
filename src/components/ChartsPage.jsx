import React from 'react';
import { LineChart, TrendingUp, PieChart, BookOpen, ShieldCheck, Layers, Activity, Microscope } from 'lucide-react';

export function ChartsPage() {
  const timeframes = ['1m', '5m', '15m', '1D'];
  const activeTimeframe = '1m';

  return (
    <div className="p-6 bg-[#0c0a09] min-h-screen">
      <h2 className="text-2xl font-bold text-white mb-4">Charts</h2>
      <p className="text-slate-400">
        Analyse one stock with candlestick charts, indicators (EMA9, EMA21, VWAP, RSI(14)),\n        and the AI Analyst read-only explanation.
      </p>

      {/* Chart card - Medium glass */}
      <section className="glass-panel rounded-2xl p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <span className="text-[11px] font-bold text-uppercase text-slate-500">
            YESBANK · <span className="text-[10px] font-medium">synthetic</span> · Candles + EMA9 / EMA21
          </span>
          <span className="text-[10px] bg-white/[0.1] px-2 py-0.5 rounded text-[10px] font-mono text-white">SIM</span>
        </div>

        {/* Timeframe pills */}
        <div className="flex gap-2">
          {timeframes.map((tf) => (
            <button
              key={tf}
              onClick={() => {}}
              className={`text-[11px] font-medium text-slate-400 transition-colors ${
                tf === activeTimeframe ? 'text-black bg-white/30 border border-white/[0.1]' : 'hover:text-white hover:bg-black/[0.04]'
              }`}
            >
              {tf}
            </button>
          ))}
        </div>

        {/* Candlestick chart placeholder with mono specs */}
        <div className="h-64 w-full rounded-xl mb-4 bg-[#1a1614] border border-white/[0.08] overflow-hidden">
          <div className="h-full w-full bg-[#1a1614]">
            {/* Candles: mono - up filled white, down hollow white outline */}
            {/* EMA9: solid white 1.5px */}
            {/* EMA21: dashed grey rgba(255,255,255,0.45) dash 4 3 */}
            {/* Volume bars: rgba(255,255,255,0.16) at bottom */}
            {/* Horizontal grid lines: var(--grid), 4 lines */}
            <svg className="w-full h-full">
              <rect width="100%" height="100%" fill="#1a1614" />
              {/* Grid lines */}
              {Array.from({ length: 4 }, (_, i) => ({
                y: (i + 1) * 25,
              })).map((p, idx) => (
                <line
                  key={idx}
                  x1="0"
                  y1={p.y}
                  x2="100%"
                  y2={p.y}
                  stroke="var(--grid)"
                  strokeWidth="1"
                />
              ))}
              {/* EMA9: solid white 1.5px */}
              <line
                x1="10%"
                y1="30%"
                x2="90%"
                y2="30%"
                stroke="var(--up)"
                strokeWidth={1.5}
              />
              {/* EMA21: dashed grey 4 3 */}
              <line
                x1="10%"
                y1="50%"
                x2="90%"
                y2="50%"
                stroke="rgba(255,255,255,0.45)"
                strokeWidth={1.5}
                strokeDasharray="4 3"
              />
            </svg>
          </div>
        </div>

        {/* Meta row */}
        <div className="flex flex-col sm:flex-row gap-2 text-[10px] text-slate-400">
          <span>RSI(14) 67</span>
          <span>Volume 1.3x Avg</span>
          <span>VWAP —</span>
          <span>EMA9 —</span>
          <span>EMA21 —</span>
        </div>
      </section>

      {/* AI Analyst card - Medium glass */}
      <section className="glass-panel rounded-2xl p-6">
        <h4 className="text-[11px] font-bold text-uppercase text-slate-500 mb-3">AI Analyst</h4>
        <p className="text-[12px] text-slate-400 leading-relaxed">
          Based on the chart pattern, RELIANCE on 1m timeframe shows a consolidation
          phase with EMA9 trending above EMA21, indicating mild bullish momentum.
          RSI(14) at 67 suggests the asset is approaching overbought territory but
          remains within healthy bounds. Volume is above average, confirming the
          price move is supported by trading activity. No immediate trigger
          identified — wait for EMA9 crossover or RSI extension for directional
          bias.
        </p>
        <button className="btn-accent w-full mt-4 text-[11px] py-2">
          Refresh
        </button>
      </section>
    </div>
  );
}