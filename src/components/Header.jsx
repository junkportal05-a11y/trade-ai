import React, { useState, useEffect } from 'react';
import { Home, Layout, Search, TrendingUp, BarChart3 } from 'lucide-react';

export default function Header({ activeTab, setActiveTab }) {
  const navItems = [
    { id: 'home', label: 'Home', icon: Home },
    { id: 'charts', label: 'Charts', icon: Layout },
    { id: 'scanner', label: 'Scanner', icon: Search },
    { id: 'predictions', label: 'Predictions', icon: TrendingUp },
    { id: 'strategies', label: 'Strategies', icon: BarChart3 },
  ];

  const [isNSEMarketOpen, setIsNSEMarketOpen] = useState(true);

  useEffect(() => {
    // Check market hours - simplified
    const checkMarket = async () => {
      // In production, use the real market data hook
      setIsNSEMarketOpen(true);
    };
    checkMarket();
  }, []);

  return (
    <header className="sticky top-0 z-50 w-full bg-black">
      {/* Brand & Navigation */}
      <div className="border-b border-white/[0.12] bg-black px-4 lg:px-8 h-14 flex items-center justify-between">
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
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
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
      </div>

      {/* Ticker tape - always visible under header */}
      <div className="ticker-tape">
        <span className="ml-4 font-mono text-[10px] tracking-wider white">
          NIFTY • TATASTEEL 43% • YESBANK BUY • RSI 67 • LIVE
        </span>
      </div>
    </header>
  );
}