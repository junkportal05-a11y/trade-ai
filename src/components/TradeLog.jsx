import React, { useState } from 'react';
import { Clock, Inbox } from 'lucide-react';

export default function TradeLog() {
  const [filter, setFilter] = useState('ALL');
  const filters = ['ALL', 'BUY', 'SELL', 'OPEN', 'ENDED'];

  return (
    <div className="glass-panel rounded-2xl p-6 space-y-4">
      {/* Top Header & Filters */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-white/[0.08]">
        <div className="flex items-center space-x-2">
          <Clock size={16} className="text-amber-400" />
          <h3 className="text-sm font-bold text-white tracking-tight">Trade Execution Log</h3>
          <span className="text-xs text-slate-500 font-mono">(Paper Journal)</span>
        </div>

        {/* Filter Segmented Control */}
        <div className="flex items-center space-x-1 bg-black p-1 rounded-xl border border-white/[0.08]">
          {filters.map((item) => (
            <button
              key={item}
              onClick={() => setFilter(item)}
              className={`px-3 py-1 text-xs rounded-lg transition-colors ${
                filter === item
                  ? 'bg-amber-500 text-black font-bold shadow-sm'
                  : 'text-slate-400 hover:text-white font-medium'
              }`}
            >
              {item}
            </button>
          ))}
        </div>
      </div>

      {/* Honest Institutional Empty State */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="border-b border-white/[0.08] text-[10px] uppercase tracking-wider text-slate-400 bg-black">
              <th className="py-3 px-4 font-semibold">Time</th>
              <th className="py-3 px-4 font-semibold">Symbol</th>
              <th className="py-3 px-4 font-semibold">Strategy</th>
              <th className="py-3 px-4 font-semibold">Side</th>
              <th className="py-3 px-4 font-semibold text-right">Qty</th>
              <th className="py-3 px-4 font-semibold text-right">Entry (₹)</th>
              <th className="py-3 px-4 font-semibold text-right">Exit (₹)</th>
              <th className="py-3 px-4 font-semibold text-right">Realized P&L</th>
              <th className="py-3 px-4 font-semibold text-center">Status</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td colSpan={9} className="py-16 text-center">
                <div className="flex flex-col items-center justify-center space-y-2.5">
                  <div className="w-11 h-11 rounded-2xl bg-black border border-white/[0.1] flex items-center justify-center text-slate-400">
                    <Inbox size={20} className="text-amber-500/80" />
                  </div>
                  <span className="text-sm font-bold text-slate-200">No trades yet</span>
                  <p className="text-xs text-slate-500 max-w-sm">
                    The bot engine is currently stopped. Start the bot or trigger a simulation run to capture intraday paper executions.
                  </p>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
