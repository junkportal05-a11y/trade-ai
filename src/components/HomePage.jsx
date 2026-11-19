import React from 'react';
import { LineChart, TrendingUp, PieChart, BookOpen, ShieldCheck, Layers, Activity, Microscope } from 'lucide-react';

const navItems = [
  { id: 'home', label: 'Home', icon: TrendingUp },
  { id: 'charts', label: 'Charts', icon: Layout },
  { id: 'scanner', label: 'Scanner', icon: Search },
  { id: 'predictions', label: 'Predictions', icon: TrendingUp },
  { id: 'strategies', label: 'Strategies', icon: BarChart3 },
];

export function HomePage({ onNavigate }) {
  const strategyWinRates = [
    { name: 'Trend Scalper', score: 50.0 },
    { name: 'Mean Reversion', score: 52.3 },
    { name: 'Breakout Volume', score: 54.6 },
    { name: 'RSI Scalper', score: 56.9 },
    { name: 'Swing Trend Follower', score: 59.2 },
  ];

  return (
    <div className="space-y-6">
      {/* Ticker tape */}
      <div className="ticker-tape">
        <span className="ml-4 font-mono text-[10px] tracking-wider white">
          NIFTY • TATASTEEL 43% • YESBANK BUY • RSI 67 • LIVE
        </span>
      </div>

      {/* Header pill */}
      <header className="header-pill border-white/[0.12] bg-black px-4 lg:px-8 h-14 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-black border border-white/[0.1] flex items-center justify-center text-slate-400 font-extrabold text-xs tracking-wider font-mono">
            AT
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-base font-extrabold text-white tracking-tight">ApexTrade</span>
            <span className="px-1.5 py-0.5 rounded bg-white/[0.05] border border-white/[0.1] text-[10px] font-mono text-slate-400 font-medium">
              v6.1.1
            </span>
            <span className="px-2 py-0.5 rounded-full bg-white/[0.05] border border-white/[0.1] text-[10px] font-bold text-white">
              PAPER ONLY
            </span>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex items-center space-x-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = item.id === 'home'; // Home is always active on Home page
            return (
              <button
                key={item.id}
                className={`px-3 py-1.5 rounded-lg text-xs transition-all flex items-center gap-1.5 ${
                  isActive
                    ? 'font-bold text-black bg-white/30 border border-white/[0.1]'
                    : 'text-slate-400 hover:text-white hover:bg-black/[0.04]'
                }`}
              >
                <Icon size={14} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </header>

      {/* Hero card - Strong glass tier */}
      <section className="mt-6 hero-card">
        <div className="kicker">AI DAILY MARKET BRIEFING</div>
        <div className="display">NIFTY <span className="up">BULLISH</span></div>
        <div className="sub-line">
          Top pick TATASTEEL 43% · Top trigger YESBANK BUY — RSI 67, Volume 1.3x Avg · No intraday trigger detected
        </div>
      </section>

      {/* Stats row - 3 cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
        <div className="stat-card">
          <div className="big-number">0.0%</div>
          <div className="caption">Prediction accuracy</div>
          <div className="caption">0 of 0 resolved</div>
        </div>
        <div className="stat-card">
          <div className="big-number">₹1,840</div>
          <div className="caption">Capital</div>
        </div>
        <div className="stat-card">
          <div className="big-number">5</div>
          <div className="caption">Prediction engines running</div>
        </div>
      </div>

      {/* Strategies row - 5 cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mt-6">
        {strategyWinRates.map((s, i) => (
          <div key={s.name} className="strategy-card">
            <div className="name">{s.name}</div>
            <div className="win-rate">{s.score}%</div>
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${s.score}%` }} />
            </div>
          </div>
        ))}
      </div>

      {/* Scanner card */}
      <section className="mt-6 glass-panel">
        <h3 className="text-[13px] font-bold text-uppercase text-slate-400 mb-4">Signal Scanner</h3>
        <p className="empty-state">No qualifying setups — the scan ran but no signal passed the gates.</p>
        <h4 className="text-[11px] font-bold text-uppercase text-slate-500 mb-2">Leaderboard</h4>
        <p className="text-[10px] text-slate-400">#1 MFI 14 Reversals — Score 16</p>
        <p className="text-[10px] text-slate-400">#2 Bollinger Bands Bounce — Score —</p>
      </section>

      {/* Engine status line */}
      <p className="text-[11px] text-slate-500 muted">
        Prediction loop running · Last scan 09:15 · Feed SIMULATED
      </p>

      {/* Links */}
      <div className="mt-6">
        <button className="btn-accent w-full">PREDICTIONS CENTRE →</button>
        <button className="btn-accent w-full mt-2">OPEN SIGNAL SCANNER →</button>
        <button className="btn-accent w-full mt-2">OPEN INTERACTIVE CHARTS →</button>
      </div>
    </div>
  );
}