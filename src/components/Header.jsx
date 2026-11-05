import React from 'react';
import { 
  Activity, 
  Search, 
  ShieldCheck, 
  Cpu, 
  Layers, 
  LineChart, 
  TrendingUp, 
  PieChart, 
  BookOpen 
} from 'lucide-react';

export default function Header({ activeTab, setActiveTab }) {
  const navItems = [
    { id: 'home', label: 'Home', icon: Activity },
    { id: 'bot', label: 'Bot Engine', icon: Cpu },
    { id: 'terminal', label: 'Terminal', icon: LineChart },
    { id: 'scanner', label: 'Scanner', icon: Layers },
    { id: 'predictions', label: 'Predictions', icon: TrendingUp },
    { id: 'analytics', label: 'Analytics', icon: PieChart },
    { id: 'journal', label: 'Journal', icon: BookOpen },
    { id: 'security', label: 'Security', icon: ShieldCheck },
  ];

  return (
    <header className="sticky top-0 z-50 w-full bg-[#050506]">
      {/* TIER 1: Ticker Strip */}
      <div className="h-8 border-b border-white/[0.08] bg-black px-4 lg:px-8 flex items-center justify-between text-xs text-slate-400 overflow-x-auto whitespace-nowrap">
        <div className="flex items-center space-x-5">
          <div className="flex items-center space-x-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500" />
            </span>
            <span className="text-[10px] font-bold tracking-wider text-amber-400 uppercase">NSE TICK FEED</span>
            <span className="px-1.5 py-0.2 rounded bg-amber-500/10 border border-amber-500/30 text-[9px] font-semibold text-amber-300 font-mono">
              SIMULATED
            </span>
          </div>

          <div className="h-3 w-[1px] bg-white/[0.1]" />

          <div className="flex items-center space-x-6 font-mono text-[11px]">
            <span>NIFTY 50: <strong className="text-amber-400 font-medium">24,180.20 (+0.32%)</strong></span>
            <span>BANKNIFTY: <strong className="text-red-400 font-medium">51,240.10 (-0.14%)</strong></span>
            <span className="flex items-center gap-1.5 text-slate-300">
              YESBANK: <strong className="text-white">₹0.00</strong>
              <span className="px-1 py-0.2 rounded bg-white/[0.06] text-[9px] text-slate-400 border border-white/[0.1]">SIM</span>
            </span>
          </div>
        </div>

        <div className="hidden md:flex items-center space-x-4 text-[11px] text-slate-500">
          <span>FEED: <strong className="text-amber-400 font-mono">SYNCHRONIZED</strong></span>
          <span>LATENCY: <strong className="text-slate-300 font-mono">11ms</strong></span>
        </div>
      </div>

      {/* TIER 2: Main Brand & Navigation Strip */}
      <div className="border-b border-white/[0.08] bg-[#070605] px-4 lg:px-8 h-14 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-400 to-amber-600 border border-amber-300 flex items-center justify-center text-black font-extrabold text-xs tracking-wider font-mono shadow-[0_0_15px_rgba(245,158,11,0.3)]">
            AT
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-base font-extrabold text-white tracking-tight">ApexTrade</span>
            <span className="px-1.5 py-0.5 rounded bg-white/[0.05] border border-white/[0.1] text-[10px] font-mono text-slate-400 font-medium">
              v6.1.1
            </span>
            <span className="px-2 py-0.5 rounded-full bg-red-500/10 border border-red-500/30 text-[10px] font-bold text-red-400">
              PAPER ONLY
            </span>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="hidden xl:flex items-center space-x-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`px-3 py-1.5 rounded-lg text-xs transition-all flex items-center gap-1.5 ${
                  isActive
                    ? 'font-bold bg-amber-500/15 text-amber-300 border border-amber-500/40 shadow-[0_0_15px_rgba(245,158,11,0.2)]'
                    : 'font-medium text-slate-400 hover:text-white hover:bg-white/[0.04]'
                }`}
              >
                <Icon size={14} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Search & Profile */}
        <div className="flex items-center space-x-3">
          <div className="relative w-44 md:w-60">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Search instruments..."
              readOnly
              className="w-full glass-input rounded-lg pl-9 pr-8 py-1.5 text-xs text-slate-200 placeholder-slate-500 cursor-pointer"
            />
            <span className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[10px] bg-black text-amber-400 px-1.5 py-0.5 rounded border border-amber-500/30 font-mono">
              ⌘K
            </span>
          </div>

          <div className="w-8 h-8 rounded-lg bg-black border border-amber-500/30 flex items-center justify-center text-xs font-black text-amber-400 font-mono">
            OW
          </div>
        </div>
      </div>

      {/* TIER 3: Portfolio & Status Strip */}
      <div className="h-11 border-b border-white/[0.08] bg-black px-4 lg:px-8 flex items-center justify-between text-xs overflow-x-auto whitespace-nowrap">
        <div className="flex items-center space-x-6 font-mono text-xs">
          <div className="flex items-center space-x-2">
            <span className="text-[11px] font-sans font-semibold text-slate-400 uppercase tracking-wider">CASH:</span>
            <span className="text-white font-medium">₹0.00</span>
          </div>
          <div className="h-3 w-[1px] bg-white/[0.1]" />
          <div className="flex items-center space-x-2">
            <span className="text-[11px] font-sans font-semibold text-slate-400 uppercase tracking-wider">HOLDINGS:</span>
            <span className="text-white font-medium">₹0.00</span>
          </div>
          <div className="h-3 w-[1px] bg-white/[0.1]" />
          <div className="flex items-center space-x-2">
            <span className="text-[11px] font-sans font-semibold text-slate-400 uppercase tracking-wider">TODAY'S P&L:</span>
            <span className="text-amber-300 bg-amber-500/10 border border-amber-500/30 px-2.5 py-0.5 rounded-full font-bold">
              +₹0.00 (0.00%)
            </span>
          </div>
        </div>

        <div className="flex items-center space-x-5">
          <div className="flex items-center space-x-2">
            <span className="text-[11px] font-sans font-semibold text-slate-400 uppercase tracking-wider">BOT ENGINE:</span>
            <span className="px-2.5 py-0.5 rounded-full bg-red-500/10 border border-red-500/40 text-[10px] font-mono font-bold text-red-400 shadow-[0_0_10px_rgba(239,68,68,0.2)]">
              STOPPED
            </span>
          </div>
          <div className="hidden sm:flex items-center space-x-1.5 text-slate-400 text-xs">
            <span className="w-2 h-2 rounded-full bg-amber-400 shadow-[0_0_8px_#f59e0b]" />
            <span className="font-medium text-slate-300">NSE: OPEN</span>
          </div>
        </div>
      </div>
    </header>
  );
}
