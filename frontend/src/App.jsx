import { API_BASE_URL, apiFetch, verifyToken } from './api';
import { Plus, Minus, Info, AlertTriangle, Link, Link2Off, RefreshCw, Layers, Crosshair, TrendingUp, X, Home, Bot, Radio, Sparkles, BarChart3, BookOpen, ShieldCheck, Activity, Wifi, WifiOff, Search, Zap, Camera, Loader2, ChevronRight, Zap as ZapIcon, RotateCcw, Database, SkipForward, Terminal, ScanLine, Settings, HelpCircle, LayoutDashboard } from 'lucide-react';
import CodeEntryScreen from './components/CodeEntryScreen';
import CandleChart from './components/CandleChart';
import { calcEMA, calcBollingerBands, calcRSI, calcMACD } from './utils/indicators';
import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { createChart, CandlestickSeries, LineSeries, HistogramSeries, createSeriesMarkers } from 'lightweight-charts';
import { useHistory, useLivePrices, isNSEMarketOpen } from './hooks/useMarketData';
import SignalsPanel from './SignalsPanel';
import IntroSplash from './IntroSplash';
import AccountPanel from './AccountPanel';
import OrderBookPanel from './OrderBookPanel';
import HomePanel from './HomePanel';
import PredictionsPanel from './PredictionsPanel';
import JournalPanel from './JournalPanel';
import SimulatorPanel from './SimulatorPanel';
import PerformancePanel from './PerformancePanel';
import BotControlPanel from './BotControlPanel';
import TradeLogPanel from './TradeLogPanel';
import StrategySelector from './StrategySelector';
import BacktestRunner from './BacktestRunner';
import { PanelErrorBoundary } from './PanelErrorBoundary';
import CommandPalette from './components/CommandPalette';
import Header from './components/Header';
import ChatPanel from './components/ChatPanel';
import TickerBar from './components/TickerBar';
import BottomConsole from './components/BottomConsole';
import WatchlistPanel from './components/WatchlistPanel';
import OrderPanel from './components/OrderPanel';
import { T, SEED_PRICES, DEFAULT_WATCHLIST, INTERVALS, PRIMARY_TABS, SECONDARY_TABS, MOBILE_TABS, TAB_META, EMPTY_ARRAY, fmt, clr, sign, escapeHTML } from './theme';

const TAB_ICONS = { Home, Bot, TrendingUp, Radio, Sparkles, BarChart3, BookOpen, ShieldCheck };

function MobileNavButtons({ view, onChange }) {
  return (
    <>
      {MOBILE_TABS.map(tab => {
        const meta = TAB_META[tab] || {};
        const Icon = TAB_ICONS[meta.icon] || Home;
        const active = view === tab;
        return (
          <button
            key={tab}
            onClick={() => onChange(tab)}
            aria-label={meta.label || tab}
            title={meta.label || tab}
            style={{
              flex: 1, padding: '10px 0', border: 'none', cursor: 'pointer',
              background: 'transparent', color: active ? T.accent : T.textDim,
              display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3,
              fontFamily: "'Inter', sans-serif", transition: 'all 0.2s',
              borderTop: `2px solid ${active ? T.accent : 'transparent'}`,
              marginTop: -1,
            }}
          >
            <Icon size={17} strokeWidth={active ? 2.4 : 2} />
            <span style={{ fontSize: 7.5, fontWeight: 700, letterSpacing: '0.04em' }}>{meta.label || tab}</span>
          </button>
        );
      })}
    </>
  );
}

// ── Tab configuration ────────────────────────────────────────────────────────
// Primary tabs: shown in the desktop header and as the main mobile bottom nav.
export default function App() {
  // Personal Workstation Mode — Single user, code-based access
  const [verified, setVerified] = useState(false);
  const [verifying, setVerifying] = useState(true);

  // Expose API base for CodeEntryScreen
  useEffect(() => {
    window.__API_BASE_URL__ = API_BASE_URL;
  }, []);

  // Verify existing token on mount
  useEffect(() => {
    let cancelled = false;
    verifyToken().then((ok) => {
      if (!cancelled) {
        setVerified(ok);
        setVerifying(false);
      }
    }).catch(() => {
      if (!cancelled) {
        setVerified(false);
        setVerifying(false);
      }
    });
    return () => { cancelled = true; };
  }, []);

  // Listen for auth-required events (401 from apiFetch)
  useEffect(() => {
    const handler = () => {
      setVerified(false);
      setVerifying(false);
    };
    window.addEventListener('apex:auth-required', handler);
    return () => window.removeEventListener('apex:auth-required', handler);
  }, []);

  // Handle successful verification from CodeEntryScreen
  const handleVerified = useCallback((data) => {
    setVerified(true);
  }, []);

  // Personal Workstation Mode — Direct Access after code verification
  // loggedIn only true after verification completes (avoids first-load race)
  const loggedIn = verified && !verifying;
  const currentUser = 'Lead Quant';
  const userRole = 'Master Quant / Administrator';
  const userClearance = 'LEVEL_4_ROOT';

  // Warm up backend in the background as soon as the app mounts
  useEffect(() => {
    const BASE_URL = API_BASE_URL;
    fetch(`${BASE_URL}/`).catch(() => {});
  }, []);

  const [view, setView]         = useState(() => {
    const pathname = window.location.pathname.toLowerCase();
    if (pathname.includes('/account') || pathname.endsWith('account')) {
      return 'ACCOUNT';
    }
    return 'SIMULATOR';
  });   // 'SIMULATOR' is default now, but routing-aware

  const [cmdOpen, setCmdOpen] = useState(false);

  const [selected, setSelected] = useState('YESBANK.NS');
  const [ivIdx, setIvIdx]       = useState(0);          // 1D default for intraday
  const [rightTab, setRightTab] = useState('BOT');
  
  const [drawMode, setDrawMode] = useState(null); // 'SUPPORT' | 'RESISTANCE' | null
  const [chartLines, setChartLines] = useState({}); // { 'AAPL.NS': [{price, type, id}] }
  
  const handleDrawComplete = useCallback((line) => {
    setChartLines(prev => ({
      ...prev,
      [selected]: [...(prev[selected] || []), line]
    }));
    setDrawMode(null); // auto-turn off drawing mode after 1 click
  }, [selected]);
  
  // Server warming/cold start splash page state
  const [serverWarming, setServerWarming] = useState(() => localStorage.getItem('apex_splash_shown') === null);
  const [backendReady, setBackendReady] = useState(false);

  // Paper Trading State
  const [portfolio, setPortfolio] = useState(() => {
    const saved = localStorage.getItem('apex_portfolio');
    return saved ? JSON.parse(saved) : []; // Default is empty portfolio: no stocks
  });
  const [cash, setCash] = useState(() => {
    const saved = localStorage.getItem('apex_cash');
    return saved ? parseFloat(saved) : 1000000; // Starting cash: ₹10,00,000 (10 Lakhs)
  });
  const [openOrders, setOpenOrders] = useState([]);

  useEffect(() => {
    localStorage.setItem('apex_portfolio', JSON.stringify(portfolio));
  }, [portfolio]);

  useEffect(() => {
    localStorage.setItem('apex_cash', cash.toString());
  }, [cash]);

  // Chart markers for executed paper trades
  const [tradeMarkers, setTradeMarkers] = useState({});

  const symbols = DEFAULT_WATCHLIST.map(w => w.symbol);
  const { prices, connected, dataSource } = useLivePrices(symbols);
  const iv = INTERVALS[ivIdx];
  const currentPrice     = prices[selected]?.price ?? SEED_PRICES[selected] ?? 0;
  const currentChangePct = prices[selected]?.changePct ?? 0;

  const totalStockValue = portfolio.reduce((sum, pos) => {
    const price = prices[pos.symbol]?.price ?? SEED_PRICES[pos.symbol] ?? pos.avgCost;
    return sum + (price * pos.shares);
  }, 0);
  const netWorth = totalStockValue + cash;

  // ── Keyboard Shortcuts ────────────────────────────────────────────────────────
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K')) {
        e.preventDefault();
        setCmdOpen(prev => !prev);
        return;
      }
      if (cmdOpen) return;
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

      if (e.key === 'b' || e.key === 'B') {
        setView('HOME');
      } else if (e.key === 's' || e.key === 'S') {
        setView('HOME');
      } else if (e.key >= '1' && e.key <= '6') {
        const idx = parseInt(e.key) - 1;
        if (idx < INTERVALS.length) {
          setIvIdx(idx);
          setView('CHART');
        }
      } else if (e.key === 'Tab') {
        e.preventDefault();
        const currentIndex = DEFAULT_WATCHLIST.findIndex(w => w.symbol === selected);
        const nextIndex = (currentIndex + 1) % DEFAULT_WATCHLIST.length;
        setSelected(DEFAULT_WATCHLIST[nextIndex].symbol);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selected, cmdOpen]);

  // ── Morning Brief ───────────────────────────────────────────────────────────
  const [showBriefModal, setShowBriefModal] = useState(false);
  const [morningSignals, setMorningSignals] = useState([]);

  // Watchlist panel state (collapsed by default - bot manages its own universe)
  const [showWatchlist, setShowWatchlist] = useState(false);
  
  useEffect(() => {
    const checkMorningBrief = () => {
      if (!loggedIn) return;
      
      const now = new Date();
      const istTime = new Date(now.toLocaleString("en-US", {timeZone: "Asia/Kolkata"}));
      const hours = istTime.getHours();
      const minutes = istTime.getMinutes();
      
      const todayStr = istTime.toDateString();
      const lastShown = localStorage.getItem('last_morning_brief');
      
      if (lastShown !== todayStr && (hours > 9 || (hours === 9 && minutes >= 15))) {
        // Market is open or opened already today
        apiFetch('/api/scan', {
          method: 'POST',
          body: JSON.stringify({ symbols: DEFAULT_WATCHLIST.map(w=>w.symbol), interval: '15m', capital: cash })
        })
        .then(r => r.json())
        .then(data => {
          if (data.signals) {
            setMorningSignals(data.signals.slice(0, 3));
            setShowBriefModal(true);
            localStorage.setItem('last_morning_brief', todayStr);
          }
        }).catch(err => console.error("Morning brief scan failed", err));
      }
    };
    
    checkMorningBrief();
    const t = setInterval(checkMorningBrief, 60000);
    return () => clearInterval(t);
  }, [cash]);

  const totalCost = portfolio.reduce((sum, pos) => {
    return sum + (pos.avgCost * pos.shares);
  }, 0);
  const totalPnl = totalStockValue - totalCost;
  const totalPct = totalCost > 0 ? (totalPnl / totalCost) * 100 : 0;

  // Mobile layout sub-tab for Chart page
  const [mobileSubTab, setMobileSubTab] = useState('CHART');

  // Bot Engine State — paper only, live trading is not exposed.
  const botPaperMode = true;
  const [selectedStrategy, setSelectedStrategy] = useState('intraday_momentum');
  const [strategyPerformance, setStrategyPerformance] = useState(null);
  const [backtestResults, setBacktestResults] = useState(null);

  // Console active tab state
  const [consoleTab, setConsoleTab] = useState('POSITIONS');

  // Price alerts state
  const [priceAlerts, setPriceAlerts] = useState(() => {
    const saved = localStorage.getItem('apex_price_alerts');
    return saved ? JSON.parse(saved) : [];
  });

  // Reference for prices to prevent unnecessary re-fetches in AI effects
  const pricesRef = useRef(prices);
  useEffect(() => {
    pricesRef.current = prices;
  }, [prices]);

  // App-level Cache for Daily Market Briefing & Stats
  const [marketBrief, setMarketBrief] = useState(null);
  const [loadingBrief, setLoadingBrief] = useState(true);
  const [predictionStats, setPredictionStats] = useState(null);
  const [refreshAnalystToken, setRefreshAnalystToken] = useState(0);

  const fetchMarketBrief = useCallback(() => {
    if (!loggedIn || !backendReady) return;
    apiFetch('/api/market_brief')
    .then(res => res.ok ? res.json() : Promise.reject())
    .then(data => {
      setMarketBrief(data);
      setLoadingBrief(false);
    })
    .catch(() => {
      setLoadingBrief(false);
    });
  }, [loggedIn]);

  const fetchPredictionStats = useCallback(() => {
    if (!loggedIn || !backendReady) return;
    apiFetch('/api/predictions/stats')
    .then(res => res.ok ? res.json() : Promise.reject())
    .then(data => {
      setPredictionStats(data);
    })
    .catch(() => {});
  }, [loggedIn]);

  useEffect(() => {
    if (loggedIn && backendReady) {
      fetchMarketBrief();
      fetchPredictionStats();
    }
  }, [loggedIn, backendReady, fetchMarketBrief, fetchPredictionStats]);

  // Watchlist favorites state
  const [favorites, setFavorites] = useState(() => {
    const saved = localStorage.getItem('apex_favorites');
    return saved ? JSON.parse(saved) : ['YESBANK.NS', 'BEL.NS'];
  });

  // AI Analyst embedded card states
  const [aiRecommendation, setAiRecommendation] = useState('');
  const [aiRecommendationLoading, setAiRecommendationLoading] = useState(false);
  const aiRecommendationCache = useRef({});
  const lastRefreshRef = useRef(0);

  // Toast notifications state
  const [toasts, setToasts] = useState([]);

  // Signals state (pre-seeded fallback, fresh scan manually triggered in Signals tab)
  const [signals, setSignals] = useState([
    { symbol: 'YESBANK.NS', name: 'HAL', signal: 'BUY', confidence: 88, rr_ratio: 2.5, reasoning: 'RSI oversold trigger on daily candle chart. Volume spike supports reversal.' },
    { symbol: 'BEL.NS', name: 'BEL', signal: 'BUY', confidence: 75, rr_ratio: 1.8, reasoning: 'Moving average convergence crossover signals strong bullish momentum.' },
    { symbol: 'RVNL.NS', name: 'RVNL', signal: 'BUY', confidence: 82, rr_ratio: 2.1, reasoning: 'Breakout patterns on high volume confirmation.' }
  ]);

  const showToast = useCallback((message, type = 'success') => {
    const id = Math.random().toString(36).substr(2, 9);
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 5000);
  }, []);

  const handleCommandAction = useCallback(async (actionId, payload) => {
    switch (actionId) {
      case 'selectSymbol':
        if (payload) setSelected(payload);
        break;
      case 'refresh-analyst':
        setRefreshAnalystToken(prev => prev + 1);
        showToast('AI analyst refresh requested', 'info');
        break;
      case 'scan-breakouts':
        setView('SIGNALS');
        break;
      case 'health-diag':
        window.dispatchEvent(new CustomEvent('apex:open-health'));
        break;
      case 'clear-logs':
        setTradeMarkers({});
        showToast('Order log markers cleared', 'info');
        break;
      case 'emergency-stop':
        try {
          const res = await apiFetch('/api/bot/stop', { method: 'POST' });
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          showToast('EMERGENCY STOP — bot halted and positions squared off', 'success');
        } catch (err) {
          showToast(`Emergency stop failed: ${err.message}`, 'error');
        }
        break;
      default:
        break;
    }
  }, [showToast]);

  const handleToggleFavorite = useCallback((symbol) => {
    setFavorites(prev => {
      const updated = prev.includes(symbol) ? prev.filter(s => s !== symbol) : [...prev, symbol];
      localStorage.setItem('apex_favorites', JSON.stringify(updated));
      return updated;
    });
  }, []);

  const handleAddAlert = useCallback((symbol, condition, targetPrice) => {
    const newAlert = {
      id: Math.random().toString(36).substr(2, 9),
      symbol,
      condition,
      targetPrice: parseFloat(targetPrice),
      active: true,
    };
    setPriceAlerts(prev => {
      const updated = [...prev, newAlert];
      localStorage.setItem('apex_price_alerts', JSON.stringify(updated));
      return updated;
    });
    showToast(`Price alert created for ${symbol.replace('.NS', '')}`, 'success');
  }, [showToast]);

  const handleDeleteAlert = useCallback((id) => {
    setPriceAlerts(prev => {
      const updated = prev.filter(a => a.id !== id);
      localStorage.setItem('apex_price_alerts', JSON.stringify(updated));
      return updated;
    });
    showToast(`Price alert removed`, 'info');
  }, [showToast]);

  const [pendingPredictions, setPendingPredictions] = useState([]);
  const resolvingIds = useRef(new Set());

  // Fetch pending predictions
  const fetchPendingPredictions = useCallback(async () => {
    if (!loggedIn) return;
    try {
      const res = await apiFetch('/api/predictions');
      if (res.ok) {
        const data = await res.json();
        setPendingPredictions(data.filter(p => p.status === 'PENDING'));
      }
    } catch (err) {
      console.error("Error fetching pending predictions:", err);
    }
  }, [loggedIn]);

  useEffect(() => {
    if (!loggedIn) return;
    fetchPendingPredictions();
    if (view === 'PREDICTIONS') {
      const interval = setInterval(fetchPendingPredictions, 60000); // refresh pending list every 60s when on Predictions view
      return () => clearInterval(interval);
    }
  }, [fetchPendingPredictions, loggedIn, view]);



  // Embedded AI Analyst Recommendation Fetch Effect
  useEffect(() => {
    if (!selected || !loggedIn || view !== 'CHART') return;

    const isManualRefresh = refreshAnalystToken !== lastRefreshRef.current;
    lastRefreshRef.current = refreshAnalystToken;

    if (aiRecommendationCache.current[selected] && !isManualRefresh) {
      setAiRecommendation(aiRecommendationCache.current[selected]);
      setAiRecommendationLoading(false);
      return;
    }

    let active = true;
    setAiRecommendationLoading(true);
    setAiRecommendation('');
    
    const timer = setTimeout(async () => {
      try {
        const cleanedSymbol = selected.replace('.NS', '');
        const currentPrices = pricesRef.current || {};
        const livePrice = currentPrices[selected]?.price ?? SEED_PRICES[selected] ?? 0;
        const pct = currentPrices[selected]?.changePct ?? 0;

        const res = await apiFetch('/api/chat', {
          method: 'POST',
          body: JSON.stringify({
            message: `Provide a quick 1-2 sentence technical analyst recommendation for ${cleanedSymbol} at current price ₹${livePrice} (${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%). Focus on technical metrics like RSI, key levels, or potential triggers. Keep it extremely concise.`,
            context: { symbol: cleanedSymbol, price: livePrice, changePct: pct },
            history: []
          })
        });
        if (res.ok && active) {
          const data = await res.json();
          setAiRecommendation(data.reply);
          aiRecommendationCache.current[selected] = data.reply;
        } else if (active) {
          const fallbackVal = `AI Recommendation unavailable (Backend Error).`;
          setAiRecommendation(fallbackVal);
          aiRecommendationCache.current[selected] = fallbackVal;
        }
      } catch (err) {
        if (active) {
          const fallbackVal = `AI Recommendation unavailable (Network Error).`;
          setAiRecommendation(fallbackVal);
          aiRecommendationCache.current[selected] = fallbackVal;
        }
      } finally {
        if (active) setAiRecommendationLoading(false);
      }
    }, 1000); // 1 second debounce
    
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [selected, loggedIn, view, refreshAnalystToken]); // Removed 'prices' dependency

  // Price Alerts Engine Effect
  useEffect(() => {
    if (priceAlerts.length === 0) return;
    
    const triggeredIds = [];
    priceAlerts.forEach(alert => {
      const liveData = prices[alert.symbol];
      if (!liveData) return;
      
      const price = liveData.price;
      let triggered = false;
      if (alert.condition === 'above' && price >= alert.targetPrice) {
        triggered = true;
      } else if (alert.condition === 'below' && price <= alert.targetPrice) {
        triggered = true;
      }
      
      if (triggered) {
        triggeredIds.push(alert.id);
        const sideSymbol = alert.symbol.replace('.NS', '');
        const direction = alert.condition === 'above' ? 'crossed above' : 'dropped below';
        showToast(`⏰ ALERT TRIGGERED: ${sideSymbol} has ${direction} ₹${fmt(alert.targetPrice, 1)} (Current: ₹${fmt(price, 1)})`, 'info');
      }
    });
    
    if (triggeredIds.length > 0) {
      setPriceAlerts(prev => {
        const updated = prev.filter(a => !triggeredIds.includes(a.id));
        localStorage.setItem('apex_price_alerts', JSON.stringify(updated));
        return updated;
      });
    }
  }, [prices, priceAlerts, showToast]);


  // Mobile Responsiveness State
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 960);
  const [mobileTab, setMobileTab] = useState('CHART'); // 'WATCHLIST' | 'CHART' | 'SIGNALS' | 'ORDER' | 'PORTFOLIO' | 'AI'

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth <= 960);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  
  // Interactive Overlays/Oscillators Toggles
  const [indicators, setIndicators] = useState({
    ema9: false,
    ema21: false,
    bb: false,
    rsi: false,
    macd: false,
  });


  const lastBarTimeRef = useRef(null);

  const handleLastBarUpdate = useCallback((time) => {
    lastBarTimeRef.current = time;
  }, []);

  const getCurrentBarTime = useCallback((interval) => {
    const now = new Date();
    if (interval === '1d' || interval === '1wk' || interval === '1mo' || interval === '3mo') {
      const yyyy = now.getFullYear();
      const mm = String(now.getMonth() + 1).padStart(2, '0');
      const dd = String(now.getDate()).padStart(2, '0');
      return `${yyyy}-${mm}-${dd}`;
    } else {
      let seconds = 300;
      if (interval === '1m') seconds = 60;
      if (interval === '5m') seconds = 300;
      if (interval === '15m') seconds = 900;
      if (interval === '30m') seconds = 1800;
      if (interval === '60m' || interval === '1h') seconds = 3600;
      const ms = seconds * 1000;
      return Math.floor(Math.floor(Date.now() / ms) * ms / 1000);
    }
  }, []);

  const addTradeMarker = useCallback((sym, side, qty, execPrice) => {
    const barTime = (sym === selected && lastBarTimeRef.current) 
      ? lastBarTimeRef.current 
      : getCurrentBarTime(INTERVALS[ivIdx].interval);

    const newMarker = {
      time: barTime,
      position: side === 'buy' ? 'belowBar' : 'aboveBar',
      color: side === 'buy' ? T.green : T.red,
      shape: side === 'buy' ? 'arrowUp' : 'arrowDown',
      text: `${side.toUpperCase()}: ${qty} @ ₹${fmt(execPrice, 1)}`,
    };

    setTradeMarkers(prev => ({
      ...prev,
      [sym]: [...(prev[sym] || []), newMarker]
    }));
  }, [selected, ivIdx, getCurrentBarTime]);



  // Execute market/limit orders
  const handleExecuteOrder = async (order) => {
    const qty = parseFloat(order.qty);
    if (isNaN(qty) || qty <= 0) {
      alert("Please enter a valid share quantity!");
      return false;
    }
    
    if (order.type === 'market') {
      const price = order.price;
      const cost = qty * price;
      
      if (order.side === 'buy') {
        if (cost > cash) {
          alert("Insufficient cash balance!");
          return false;
        }
        setCash(prev => prev - cost);
        setPortfolio(prev => {
          const existing = prev.find(p => p.symbol === order.symbol);
          if (existing) {
            const newShares = existing.shares + qty;
            const newAvgCost = ((existing.shares * existing.avgCost) + cost) / newShares;
            return prev.map(p => p.symbol === order.symbol ? { ...p, shares: newShares, avgCost: newAvgCost } : p);
          } else {
            return [...prev, { symbol: order.symbol, shares: qty, avgCost: price }];
          }
        });
        addTradeMarker(order.symbol, 'buy', qty, price);
      } else {
        // sell
        let valid = true;
        setPortfolio(prev => {
          const existing = prev.find(p => p.symbol === order.symbol);
          if (!existing || existing.shares < qty) {
            valid = false;
            return prev;
          }
          const newShares = existing.shares - qty;
          if (newShares === 0) {
            return prev.filter(p => p.symbol !== order.symbol);
          }
          return prev.map(p => p.symbol === order.symbol ? { ...p, shares: newShares } : p);
        });
        
        if (!valid) {
          alert("Insufficient shares in portfolio to execute sell!");
          return false;
        }
        setCash(prev => prev + cost);
        addTradeMarker(order.symbol, 'sell', qty, price);
      }

      // Persist to backend Journal
      try {
        await apiFetch('/api/journal', {
          method: 'POST',
          body: JSON.stringify({
            symbol: order.symbol,
            direction: order.side.toUpperCase(),
            entry_price: price,
            qty: qty,
            reason: 'Manual Paper Trade',
            status: order.side === 'buy' ? 'OPEN' : 'CLOSED',
            emotion: 'Calm'
          })
        });
      } catch (e) {
        console.error("Failed to log paper trade to journal", e);
      }

      return 'filled';
    } else {
      // limit order
      const limitPrice = parseFloat(order.limitPrice);
      if (isNaN(limitPrice) || limitPrice <= 0) {
        alert("Please enter a valid limit price!");
        return false;
      }
      
      if (order.side === 'buy' && qty * limitPrice > cash) {
        alert("Insufficient cash to place this limit order!");
        return false;
      }
      
      if (order.side === 'sell') {
        const existing = portfolio.find(p => p.symbol === order.symbol);
        const lockedShares = openOrders
          .filter(o => o.symbol === order.symbol && o.side === 'sell')
          .reduce((sum, o) => sum + o.qty, 0);
        if (!existing || existing.shares < lockedShares + qty) {
          alert("Insufficient shares available (some are locked in other open orders)!");
          return false;
        }
      }

      const newOrder = {
        id: Math.random().toString(36).substr(2, 9),
        symbol: order.symbol,
        side: order.side,
        qty,
        limitPrice,
        timestamp: Date.now()
      };
      
      setOpenOrders(prev => [...prev, newOrder]);
      return 'placed';
    }
  };

  const handleCancelOrder = (id) => {
    setOpenOrders(prev => prev.filter(o => o.id !== id));
  };

  // Limit Order Matching Engine (Check on price ticks)
  useEffect(() => {
    if (openOrders.length === 0) return;
    
    let filledIds = [];
    let updatedCash = cash;
    let updatedPortfolio = [...portfolio];
    
    openOrders.forEach(order => {
      const livePrice = prices[order.symbol]?.price;
      if (!livePrice) return;
      
      let trigger = false;
      if (order.side === 'buy' && livePrice <= order.limitPrice) {
        trigger = true;
      } else if (order.side === 'sell' && livePrice >= order.limitPrice) {
        trigger = true;
      }
      
      if (trigger) {
        filledIds.push(order.id);
        const cost = order.qty * order.limitPrice; // execute at limit price
        addTradeMarker(order.symbol, order.side, order.qty, order.limitPrice);
        
        if (order.side === 'buy') {
          if (cost <= updatedCash) {
            updatedCash -= cost;
            const existingIdx = updatedPortfolio.findIndex(p => p.symbol === order.symbol);
            if (existingIdx !== -1) {
              const existing = updatedPortfolio[existingIdx];
              const newShares = existing.shares + order.qty;
              const newAvgCost = ((existing.shares * existing.avgCost) + cost) / newShares;
              updatedPortfolio[existingIdx] = { ...existing, shares: newShares, avgCost: newAvgCost };
            } else {
              updatedPortfolio.push({ symbol: order.symbol, shares: order.qty, avgCost: order.limitPrice });
            }
          }
        } else {
          // sell
          const existingIdx = updatedPortfolio.findIndex(p => p.symbol === order.symbol);
          if (existingIdx !== -1) {
            const existing = updatedPortfolio[existingIdx];
            if (existing.shares >= order.qty) {
              const newShares = existing.shares - order.qty;
              if (newShares === 0) {
                updatedPortfolio.splice(existingIdx, 1);
              } else {
                updatedPortfolio[existingIdx] = { ...existing, shares: newShares };
              }
              updatedCash += cost;
            }
          }
        }
      }
    });
    
    if (filledIds.length > 0) {
      setCash(updatedCash);
      setPortfolio(updatedPortfolio);
      setOpenOrders(prev => prev.filter(o => !filledIds.includes(o.id)));
    }
  }, [prices, openOrders, cash, portfolio, addTradeMarker]);

  // Called from SignalsPanel when user clicks a signal card
  const handleSignalSelect = (symbol) => {
    setSelected(symbol);
    setView('CHART');
    setIvIdx(0);  // Switch to 1D (5-min) for intraday
  };

  const handleWokenUp = useCallback(() => {
    setServerWarming(false);
    setBackendReady(true);
    localStorage.setItem('apex_splash_shown', 'true');
  }, []);
  // Personal Mode — Direct Access

  return (
    <>
      {serverWarming && <IntroSplash onWokenUp={handleWokenUp} />}
      {/* Toast Notifications */}
      <div style={{ position: 'fixed', top: 20, right: 20, zIndex: 999999, display: 'flex', flexDirection: 'column', gap: 10, maxWidth: 360 }}>
        {toasts.map(t => (
          <div key={t.id} style={{
            background: T.surface,
            border: `1px solid ${t.type === 'error' ? T.red : t.type === 'info' ? T.blue : T.green}`,
            boxShadow: `0 4px 16px rgba(0,0,0,0.5)`,
            color: T.text,
            padding: '12px 16px',
            borderRadius: 8,
            fontSize: 12,
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            animation: 'slideIn 0.3s ease',
            backdropFilter: 'blur(8px)',
          }}>
            <span style={{ color: t.type === 'error' ? T.red : t.type === 'info' ? T.blue : T.green }}>
              {t.type === 'error' ? '!' : t.type === 'info' ? 'i' : '✓'}
            </span>
            <span>{t.message}</span>
          </div>
        ))}
      </div>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&family=Inter:wght@400;500;600;700&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        html, body, #root { width: 100%; height: 100%; overflow: hidden; background: ${T.bg}; }
        ::-webkit-scrollbar { width: 3px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: ${T.borderHi}; border-radius: 2px; }
        ::-webkit-scrollbar-thumb:hover { background: ${T.accent}; }
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes pulse { 0%,100% { opacity:1; transform:scale(1); } 50% { opacity:0.5; transform:scale(0.85); } }
        @keyframes bounce { 0%,100% { transform:translateY(0); } 50% { transform:translateY(-5px); } }
        @keyframes marquee { from { transform: translateX(0); } to { transform: translateX(-50%); } }
        @keyframes fadeIn { from { opacity:0; transform:translateY(6px); } to { opacity:1; transform:translateY(0); } }
        @keyframes slideIn { from { opacity:0; transform:translateX(8px); } to { opacity:1; transform:translateX(0); } }
        @keyframes shimmer { 0%,100% { opacity:0.6; } 50% { opacity:1; } }
        button:active { transform: scale(0.97); }
      `}</style>

      {/* Auth gate — show code entry screen if not verified */}
      {verifying && (
        <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#0b0e13' }}>
          <div style={{ color: '#8290ad', fontSize: 13, fontFamily: "'IBM Plex Mono', monospace" }}>Verifying session...</div>
        </div>
      )}
      {!verifying && !verified && (
        <CodeEntryScreen onVerified={handleVerified} />
      )}
      {verified && (
        <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
        {/* Ticker bar */}
        <TickerBar prices={prices} dataSource={dataSource} />

        {/* Reconnecting banner if backend offline */}
        {!connected && (
          <div style={{
            background: 'rgba(245,200,66,0.08)',
            borderBottom: `1px solid rgba(245,200,66,0.2)`,
            color: '#f5c842',
            padding: '6px 16px',
            fontSize: 10,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 8,
            fontFamily: "'IBM Plex Mono', monospace",
            animation: 'shimmer 2s infinite',
            letterSpacing: '0.04em',
            flexShrink: 0
          }}>
            <span style={{ display: 'inline-block', width: 12, height: 12, border: `2px solid rgba(245,200,66,0.3)`, borderTopColor: '#f5c842', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
            CONNECTING TO QUANT SERVER...
          </div>
        )}

        {/* Header */}
        <Header 
          connected={connected} 
          view={view} 
          onViewChange={setView} 
          isMobile={isMobile} 

          netWorth={netWorth}
          cash={cash}
          stockValue={totalStockValue}
          totalPnl={totalPnl}
          totalPct={totalPct}
          selectedSymbol={selected}
          prices={prices}
          dataSource={dataSource}
          onCommandPaletteOpen={() => setCmdOpen(true)}
        />

        {/* Main layout */}
        <div style={{ flex: 1, display: 'flex', minHeight: 0, overflow: 'hidden' }}>

          {view === 'HOME' ? (
            /* HOME VIEW — full width */
            <div className="panel-transition" style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
              <HomePanel 
                prices={prices} 
                portfolio={portfolio} 
                cash={cash} 
                onViewChange={setView} 
                onSelectSymbol={setSelected}
                signals={signals}
                priceAlerts={priceAlerts} 
                onDeleteAlert={handleDeleteAlert} 
                brief={marketBrief}
                loadingBrief={loadingBrief}
                stats={predictionStats}
                onRefreshBrief={fetchMarketBrief}
                onUpdateBalances={(newCash, newPortfolio) => {
                  setCash(newCash);
                  setPortfolio(newPortfolio);
                }}
              />
              {isMobile && (
                <div style={{ display: 'flex', borderTop: `1px solid ${T.border}`, background: T.panelAlt, flexShrink: 0, paddingBottom: 'env(safe-area-inset-bottom)' }}>
                  <MobileNavButtons view={view} onChange={setView} />
                </div>
              )}
            </div>
          ) : view === 'SIGNALS' ? (
            /* SIGNALS VIEW — full width */
            <div className="panel-transition" style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
              <SignalsPanel onSelectSymbol={handleSignalSelect} selectedSymbol={selected} prices={prices} cash={cash} />
              {isMobile && (
                <div style={{ display: 'flex', borderTop: `1px solid ${T.border}`, background: T.panelAlt, flexShrink: 0, paddingBottom: 'env(safe-area-inset-bottom)' }}>
                  <MobileNavButtons view={view} onChange={setView} />
                </div>
              )}
            </div>
          ) : view === 'PREDICTIONS' ? (
            /* PREDICTIONS VIEW — full width */
            <div className="panel-transition" style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
              <PredictionsPanel prices={prices} selectedSymbol={selected} onSelectSymbol={setSelected} onViewChange={setView} />
              {isMobile && (
                <div style={{ display: 'flex', borderTop: `1px solid ${T.border}`, background: T.panelAlt, flexShrink: 0, paddingBottom: 'env(safe-area-inset-bottom)' }}>
                  <MobileNavButtons view={view} onChange={setView} />
                </div>
              )}
            </div>
          ) : view === 'JOURNAL' ? (
            /* JOURNAL VIEW — full width */
            <div className="panel-transition" style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
              <JournalPanel />
              {isMobile && (
                <div style={{ display: 'flex', borderTop: `1px solid ${T.border}`, background: T.panelAlt, flexShrink: 0, paddingBottom: 'env(safe-area-inset-bottom)' }}>
                  <MobileNavButtons view={view} onChange={setView} />
                </div>
              )}
            </div>
          ) : view === 'PERFORMANCE' ? (
            /* PERFORMANCE VIEW — full width */
            <div className="panel-transition" style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
              <PerformancePanel onViewChange={setView} />
              {isMobile && (
                <div style={{ display: 'flex', borderTop: `1px solid ${T.border}`, background: T.panelAlt, flexShrink: 0, paddingBottom: 'env(safe-area-inset-bottom)' }}>
                  <MobileNavButtons view={view} onChange={setView} />
                </div>
              )}
            </div>
          ) : view === 'ACCOUNT' ? (
            /* ACCOUNT VIEW — full width */
            <div className="panel-transition" style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
              <AccountPanel 
                currentUser={currentUser} 
                userRole={userRole} 
                userClearance={userClearance} 
              />
              {isMobile && (
                <div style={{ display: 'flex', borderTop: `1px solid ${T.border}`, background: T.panelAlt, flexShrink: 0, paddingBottom: 'env(safe-area-inset-bottom)' }}>
                  <MobileNavButtons view={view} onChange={setView} />
                </div>
              )}
            </div>
          ) : view === 'SIMULATOR' ? (
            /* BOT ENGINE VIEW — Hero panel: BotControl + TradeLog + Strategy + Backtest */
            <div className="panel-transition" style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16, padding: 16, flex: 1, overflow: 'auto' }}>
                {/* Top Row: Bot Control + Trade Log */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, minHeight: 0 }}>
                  <BotControlPanel />
                  <TradeLogPanel />
                </div>

                {/* Bottom Row: Strategy Selector + Backtest Runner */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, minHeight: 0 }}>
                  <StrategySelector
                    selectedStrategy={selectedStrategy}
                    onSelectStrategy={setSelectedStrategy}
                    performanceData={backtestResults?.performance}
                  />
                  <BacktestRunner onResults={setBacktestResults} />
                </div>
              </div>

              {isMobile && (
                <div style={{ display: 'flex', borderTop: `1px solid ${T.border}`, background: T.panelAlt, flexShrink: 0, paddingBottom: 'env(safe-area-inset-bottom)' }}>
                  <MobileNavButtons view={view} onChange={setView} />
                </div>
              )}
            </div>
          ) : (
            <>
              {isMobile ? (
                /* MOBILE VIEW — Single column with bottom tabs and top sub-tabs for Chart view */
                <div className="panel-transition" style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, background: T.bg }}>
                  {/* Content Area */}
                  <div style={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column' }}>
                    {/* Sub-tab switcher */}
                    <div style={{ display: 'flex', background: T.panelAlt, borderBottom: `1px solid ${T.border}`, flexShrink: 0 }}>
                      {['WATCHLIST', 'CHART', 'ORDER', 'AI'].map(sub => (
                        <button key={sub} onClick={() => setMobileSubTab(sub)} style={{
                          flex: 1, padding: '10px 0', border: 'none', cursor: 'pointer',
                          background: 'transparent',
                          color: mobileSubTab === sub ? T.accent : T.textDim,
                          fontSize: 10, fontWeight: 700,
                          fontFamily: "'Inter', sans-serif",
                          borderBottom: `2px solid ${mobileSubTab === sub ? T.accent : 'transparent'}`,
                          marginTop: -1
                        }}>
                          {sub === 'WATCHLIST' ? 'WATCH' : sub === 'CHART' ? 'CHART' : sub === 'ORDER' ? 'TRADE' : 'AI'}
                        </button>
                      ))}
                    </div>

                    {mobileSubTab === 'WATCHLIST' && (
                      <div style={{ flex: 1, background: T.surface }}>
                        <WatchlistPanel prices={prices} selected={selected} onSelect={(s) => { setSelected(s); setMobileSubTab('CHART'); }} favorites={favorites} onToggleFavorite={handleToggleFavorite} />
                      </div>
                    )}

                    {mobileSubTab === 'CHART' && (
                      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
                        {/* Interval picker & Indicator Toggles (Scrollable on mobile) */}
                        <div style={{ padding: '8px 12px', borderBottom: `1px solid ${T.border}`, display: 'flex', alignItems: 'center', gap: 6, background: T.surface, overflowX: 'auto', flexShrink: 0, whiteSpace: 'nowrap' }}>
                          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 2, padding: 2, background: T.bg, border: `1px solid ${T.border}`, borderRadius: 8, flexShrink: 0 }}>
                            {INTERVALS.map((intv, i) => (
                              <button key={intv.label} onClick={() => setIvIdx(i)} style={{
                                padding: '4px 9px', borderRadius: 6, cursor: 'pointer', fontSize: 10.5, fontWeight: 600,
                                border: `1px solid ${ivIdx === i ? 'rgba(99, 102, 241, 0.35)' : 'transparent'}`,
                                background: ivIdx === i ? `linear-gradient(135deg, ${T.accentDim}, rgba(168, 85, 247, 0.08))` : 'transparent',
                                boxShadow: ivIdx === i ? `0 0 12px ${T.accentGlow}` : 'none',
                                color: ivIdx === i ? '#fff' : T.textMid,
                                fontFamily: "'Inter', sans-serif",
                                transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)', flexShrink: 0
                              }}>{intv.label}</button>
                            ))}
                          </div>
                          <div style={{ width: 1, height: 16, background: T.border, margin: '0 4px', flexShrink: 0 }} />
                          {/* Indicator Toggles */}
                          {[
                            ['ema9', 'EMA9'], ['ema21', 'EMA21'], ['bb', 'BB'], ['rsi', 'RSI'], ['macd', 'MACD'],
                          ].map(([key, label]) => {
                            const active = indicators[key];
                            return (
                              <button key={key} onClick={() => setIndicators(prev => ({ ...prev, [key]: !prev[key] }))} style={{
                                padding: '4px 8px', border: `1px solid ${active ? T.accent : T.border}`,
                                borderRadius: 5, cursor: 'pointer', fontSize: 9, fontWeight: 700,
                                background: active ? T.accentDim : 'transparent',
                                color: active ? T.accentAlt : T.textDim,
                                fontFamily: "'Inter', sans-serif",
                                transition: 'all 0.15s', flexShrink: 0
                              }}>{label}</button>
                            );
                          })}
                          
                          <div style={{ width: 1, height: 16, background: T.border, margin: '0 4px', flexShrink: 0 }} />
                          
                          <button onClick={() => setDrawMode(drawMode === 'SUPPORT' ? null : 'SUPPORT')} style={{
                            padding: '4px 8px', border: `1px solid ${drawMode === 'SUPPORT' ? T.green : T.border}`,
                            borderRadius: 5, cursor: 'pointer', fontSize: 9, fontWeight: 700,
                            background: drawMode === 'SUPPORT' ? T.greenDim : 'transparent',
                            color: drawMode === 'SUPPORT' ? T.green : T.textDim,
                            fontFamily: "'Inter', sans-serif", transition: 'all 0.15s', flexShrink: 0
                          }}>DRAW SUPPORT</button>
                          
                          <button onClick={() => setDrawMode(drawMode === 'RESISTANCE' ? null : 'RESISTANCE')} style={{
                            padding: '4px 8px', border: `1px solid ${drawMode === 'RESISTANCE' ? T.red : T.border}`,
                            borderRadius: 5, cursor: 'pointer', fontSize: 9, fontWeight: 700,
                            background: drawMode === 'RESISTANCE' ? T.redDim : 'transparent',
                            color: drawMode === 'RESISTANCE' ? T.red : T.textDim,
                            fontFamily: "'Inter', sans-serif", transition: 'all 0.15s', flexShrink: 0
                          }}>DRAW RESIST</button>
                        </div>
                        {/* Chart */}
                        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
                          <CandleChart 
                            key={`${selected}-${INTERVALS[ivIdx].interval}-${INTERVALS[ivIdx].range}-${indicators.rsi}-${indicators.macd}`} 
                            symbol={selected} 
                            interval={INTERVALS[ivIdx].interval} 
                            range={INTERVALS[ivIdx].range} 
                            indicators={indicators} 
                            livePrice={prices[selected]}
                            markers={tradeMarkers[selected] || EMPTY_ARRAY}
                            onLastBarUpdate={handleLastBarUpdate}
                            drawMode={drawMode}
                            onDrawComplete={handleDrawComplete}
                            customLines={chartLines[selected] || EMPTY_ARRAY}
                            botPaperMode={botPaperMode}
                            dataSource={dataSource[selected]}
                          />
                        </div>
                        {/* Embedded AI Analyst Card */}
                        <div style={{
                          margin: '8px 12px 12px',
                          background: T.panel,
                          border: `1px solid ${T.border}`,
                          borderRadius: 8,
                          padding: '10px 12px',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: 6,
                          flexShrink: 0
                        }}>
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', color: T.accentAlt }}>
                              <Sparkles size={12} /> AI QUANT ANALYST: {selected.replace('.NS', '')}
                            </div>
                            {aiRecommendationLoading && (
                              <span style={{ display: 'inline-block', width: 10, height: 10, border: `1.5px solid ${T.border}`, borderTopColor: T.accentAlt, borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />
                            )}
                          </div>
                          <div style={{ fontSize: 11, color: T.text, lineHeight: 1.4 }}>
                            {aiRecommendationLoading ? (
                              <span style={{ color: T.textDim }}>Running technical scan...</span>
                            ) : (
                              aiRecommendation || "Select a ticker from the watchlist to fetch a quick technical recommendation."
                            )}
                          </div>
                          <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
                            <button
                              onClick={() => setView('PREDICTIONS')}
                              style={{
                                padding: '3px 8px',
                                background: 'rgba(245, 200, 66, 0.08)',
                                border: `1px solid ${'#f5c842'}30`,
                                borderRadius: 5,
                                color: '#f5c842',
                                fontSize: 9,
                                fontWeight: 700,
                                cursor: 'pointer',
                                fontFamily: "'Inter', sans-serif",
                                letterSpacing: '0.04em',
                                transition: 'all 0.2s'
                              }}
                              onMouseEnter={e => e.currentTarget.style.background = 'rgba(245, 200, 66, 0.15)'}
                              onMouseLeave={e => e.currentTarget.style.background = 'rgba(245, 200, 66, 0.08)'}
                            >
                              LOG PREDICTION
                            </button>
                            <button
                              onClick={() => setRefreshAnalystToken(prev => prev + 1)}
                              disabled={aiRecommendationLoading}
                              style={{
                                padding: '3px 8px',
                                background: 'rgba(77, 166, 255, 0.08)',
                                border: `1px solid ${T.blue}30`,
                                borderRadius: 5,
                                color: T.blue,
                                fontSize: 9,
                                fontWeight: 700,
                                cursor: aiRecommendationLoading ? 'not-allowed' : 'pointer',
                                fontFamily: "'Inter', sans-serif",
                                letterSpacing: '0.04em',
                                transition: 'all 0.2s'
                              }}
                              onMouseEnter={e => !aiRecommendationLoading && (e.currentTarget.style.background = 'rgba(77, 166, 255, 0.15)')}
                              onMouseLeave={e => !aiRecommendationLoading && (e.currentTarget.style.background = 'rgba(77, 166, 255, 0.08)')}
                            >
                    REFRESH
                            </button>
                          </div>
                        </div>
                      </div>
                    )}

                    {mobileSubTab === 'ORDER' && (
                      <div style={{ flex: 1, background: T.surface, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
                        <div style={{ flex: '1 1 50%', overflowY: 'auto', minHeight: 0 }}>
                          <OrderPanel symbol={selected} price={currentPrice} cash={cash} openOrders={openOrders} onExecuteOrder={handleExecuteOrder} onCancelOrder={handleCancelOrder} priceAlerts={priceAlerts} onAddAlert={handleAddAlert} onDeleteAlert={handleDeleteAlert} />
                        </div>
                        <div style={{ flex: '1 1 50%', minHeight: 0 }}>
                          <OrderBookPanel symbol={selected} price={currentPrice} />
                        </div>
                      </div>
                    )}

                    {mobileSubTab === 'AI' && (
                      <div style={{ flex: 1, background: T.surface }}>
                        <ChatPanel symbol={selected} price={currentPrice} changePct={currentChangePct} />
                      </div>
                    )}
                  </div>

                  {/* Bottom Navigation Bar */}
                  <div style={{ display: 'flex', borderTop: `1px solid ${T.border}`, background: T.panelAlt, flexShrink: 0, paddingBottom: 'env(safe-area-inset-bottom)' }}>
                    <MobileNavButtons view={view} onChange={setView} />
                  </div>
                </div>
              ) : (
                /* DESKTOP VIEW — 3 Columns (Watchlist collapsible) */
                <div className="panel-transition" style={{ flex: 1, display: 'flex', minHeight: 0, overflow: 'hidden' }}>
                  {/* LEFT — Watchlist (Collapsible) */}
                  <div style={{ width: showWatchlist ? 280 : 0, flexShrink: 0, borderRight: showWatchlist ? `1px solid ${T.border}` : 'none', background: T.surface, overflow: 'hidden', transition: 'width 0.3s ease, border 0.3s ease' }}>
                    {showWatchlist && (
                      <WatchlistPanel prices={prices} selected={selected} onSelect={setSelected} favorites={favorites} onToggleFavorite={handleToggleFavorite} />
                    )}
                  </div>

                  {/* Watchlist Toggle Button */}
                  <button
                    onClick={() => setShowWatchlist(!showWatchlist)}
                    style={{
                      position: 'relative',
                      width: 32,
                      flexShrink: 0,
                      border: 'none',
                      background: T.surface,
                      borderRight: `1px solid ${T.border}`,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      transition: 'background 0.2s'
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = T.panelAlt}
                    onMouseLeave={e => e.currentTarget.style.background = T.surface}
                    aria-label={showWatchlist ? 'Collapse watchlist' : 'Expand watchlist'}
                  >
                    <span style={{
                      fontSize: 14,
                      color: showWatchlist ? T.accent : T.textMid,
                      transform: showWatchlist ? 'rotate(180deg)' : 'rotate(0deg)',
                      transition: 'transform 0.3s ease, color 0.2s'
                    }}>
                      ◀
                    </span>
                  </button>

                  {/* CENTER — Chart and Bottom Console */}
                  <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, background: T.bg }}>
                    {/* Interval picker & Indicator Toggles */}
                    <div style={{ padding: '8px 16px', borderBottom: `1px solid ${T.border}`, display: 'flex', alignItems: 'center', gap: 6, background: T.surface, flexWrap: 'wrap' }}>
                      <div style={{ display: 'inline-flex', alignItems: 'center', gap: 2, padding: 2, background: T.bg, border: `1px solid ${T.border}`, borderRadius: 8 }}>
                        {INTERVALS.map((intv, i) => (
                          <button key={intv.label} onClick={() => setIvIdx(i)} style={{
                            padding: '4px 11px', borderRadius: 6, cursor: 'pointer', fontSize: 10.5, fontWeight: 600,
                            border: `1px solid ${ivIdx === i ? 'rgba(99, 102, 241, 0.35)' : 'transparent'}`,
                            background: ivIdx === i ? `linear-gradient(135deg, ${T.accentDim}, rgba(168, 85, 247, 0.08))` : 'transparent',
                            boxShadow: ivIdx === i ? `0 0 12px ${T.accentGlow}` : 'none',
                            color: ivIdx === i ? '#fff' : T.textMid,
                            fontFamily: "'Inter', sans-serif", letterSpacing: '0.02em',
                            transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
                          }}>{intv.label}</button>
                        ))}
                      </div>

                      <div style={{ width: 1, height: 16, background: T.border, margin: '0 8px' }} />

                      {/* Indicator Toggles */}
                      {[
                        ['ema9', 'EMA 9'],
                        ['ema21', 'EMA 21'],
                        ['bb', 'BB Bands'],
                        ['rsi', 'RSI'],
                        ['macd', 'MACD'],
                      ].map(([key, label]) => {
                        const active = indicators[key];
                        return (
                          <button key={key} onClick={() => setIndicators(prev => ({ ...prev, [key]: !prev[key] }))} style={{
                            padding: '4px 9px', border: `1px solid ${active ? T.accent : T.border}`,
                            borderRadius: 5, cursor: 'pointer', fontSize: 9, fontWeight: 700,
                            background: active ? T.accentDim : 'transparent',
                            color: active ? T.accentAlt : T.textDim,
                            fontFamily: "'Inter', sans-serif", letterSpacing: '0.04em',
                            transition: 'all 0.15s',
                          }}>{label}</button>
                        );
                      })}

                      <div style={{ marginLeft: 'auto', fontSize: 10, color: T.textDim, fontFamily: "'IBM Plex Mono', monospace" }}>
                        {INTERVALS[ivIdx].interval} · {INTERVALS[ivIdx].range}
                      </div>
                    </div>

                    {/* Chart */}
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
                      <CandleChart
                        key={`${selected}-${INTERVALS[ivIdx].interval}-${INTERVALS[ivIdx].range}-${indicators.rsi}-${indicators.macd}`}
                        symbol={selected}
                        interval={INTERVALS[ivIdx].interval}
                        range={INTERVALS[ivIdx].range}
                        indicators={indicators}
                        livePrice={prices[selected]}
                        markers={tradeMarkers[selected] || EMPTY_ARRAY}
                        onLastBarUpdate={handleLastBarUpdate}
                        botPaperMode={botPaperMode}
                        dataSource={dataSource[selected]}
                      />
                    </div>

                    {/* Bottom Console Tray */}
                    <BottomConsole 
                      prices={prices} 
                      portfolio={portfolio} 
                      cash={cash} 
                      openOrders={openOrders} 
                      onCancelOrder={handleCancelOrder} 
                      priceAlerts={priceAlerts} 
                      onDeleteAlert={handleDeleteAlert}
                      aiRecommendation={aiRecommendation}
                      aiRecommendationLoading={aiRecommendationLoading}
                      selected={selected}
                      onExecuteOrder={handleExecuteOrder}
                      onViewChange={setView}
                      consoleTab={consoleTab}
                      setConsoleTab={setConsoleTab}
                      onRefreshAnalyst={() => setRefreshAnalystToken(prev => prev + 1)}
                    />
                  </div>

                  {/* RIGHT — Tabbed panel (Bot Engine) */}
                  <div style={{ width: 360, flexShrink: 0, borderLeft: `1px solid ${T.border}`, background: T.surface, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                    {/* Tab header */}
                    <div style={{ display: 'flex', borderBottom: `1px solid ${T.border}`, flexShrink: 0, background: T.panelAlt }}>
                      {['BOT ENGINE', 'TRADE LOG', 'STRATEGIES', 'BACKTEST'].map(tab => (
                        <button key={tab} onClick={() => setRightTab(tab)} style={{
                          flex: 1, padding: '10px 4px', border: 'none', cursor: 'pointer',
                          background: 'transparent',
                          borderBottom: `2px solid ${rightTab === tab ? T.accent : 'transparent'}`,
                          color: rightTab === tab ? T.text : T.textDim,
                          fontSize: 8.5, fontWeight: 700, letterSpacing: '0.04em',
                          fontFamily: "'Inter', sans-serif", transition: 'all 0.2s',
                        }}>
                          {tab}
                        </button>
                      ))}
                    </div>
                    {/* Tab content */}
                    <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                      {rightTab === 'BOT ENGINE' && (
                        <div style={{ flex: 1, overflow: 'hidden', padding: 12 }}>
                          <BotControlPanel />
                        </div>
                      )}
                      {rightTab === 'TRADE LOG' && (
                        <div style={{ flex: 1, overflow: 'hidden', padding: 12 }}>
                          <TradeLogPanel />
                        </div>
                      )}
                      {rightTab === 'STRATEGIES' && (
                        <div style={{ flex: 1, overflow: 'hidden', padding: 12 }}>
                          <StrategySelector selectedStrategy={selectedStrategy} onSelectStrategy={setSelectedStrategy} performanceData={strategyPerformance} />
                        </div>
                      )}
                      {rightTab === 'BACKTEST' && (
                        <div style={{ flex: 1, overflow: 'hidden', padding: 12 }}>
                          <BacktestRunner onResults={setBacktestResults} />
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
        
        <CommandPalette
          isOpen={cmdOpen}
          onClose={() => setCmdOpen(false)}
          onViewChange={setView}
          onAction={handleCommandAction}
          currentView={view}
          selectedSymbol={selected}
          prices={prices}
        />

        {/* Morning Brief Modal */}
        {showBriefModal && (
          <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.85)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999, padding: 20 }}>
            <div style={{ background: T.surface, padding: 30, borderRadius: 12, border: `1px solid ${T.accent}`, width: '100%', maxWidth: 500, display: 'flex', flexDirection: 'column', gap: 20, boxShadow: `0 0 40px ${T.accentDim}` }}>
              <div>
                <h2 style={{ margin: 0, color: T.text, fontFamily: "'IBM Plex Mono', monospace", fontSize: 18 }}>MORNING MARKET BRIEF</h2>
                <div style={{ color: T.textMid, fontSize: 12, marginTop: 4 }}>Top 3 algorithmic signals for today's open.</div>
              </div>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {morningSignals.length === 0 ? (
                  <div style={{ color: T.textMid, fontSize: 13, textAlign: 'center', padding: 20 }}>No high-confidence signals found at open.</div>
                ) : morningSignals.map((s, i) => (
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: 16, background: T.bg, border: `1px solid ${T.borderHi}`, borderRadius: 8 }}>
                    <div>
                      <div style={{ color: T.text, fontWeight: 'bold', fontFamily: "'IBM Plex Mono', monospace" }}>{s.symbol}</div>
                      <div style={{ color: s.action === 'BUY' ? T.green : T.red, fontSize: 12, fontWeight: 'bold' }}>{s.action} @ ₹{fmt(s.current_price)}</div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ color: T.textMid, fontSize: 11 }}>Target: <span style={{color: T.text}}>₹{fmt(s.target)}</span></div>
                      <div style={{ color: T.textMid, fontSize: 11 }}>Stop: <span style={{color: T.text}}>₹{fmt(s.stop_loss)}</span></div>
                    </div>
                  </div>
                ))}
              </div>
              
              <button onClick={() => setShowBriefModal(false)} style={{ background: T.accent, color: '#fff', border: 'none', padding: '12px', borderRadius: 6, fontWeight: 'bold', cursor: 'pointer', fontFamily: "'IBM Plex Mono', monospace", marginTop: 10 }}>ACKNOWLEDGE</button>
            </div>
          </div>
        )}
      </div>
      )}
    </>
  );
}

