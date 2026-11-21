import { API_BASE_URL, apiFetch, verifyToken } from './api';
import { Plus, Minus, Info, AlertTriangle, Link, Link2Off, RefreshCw, Layers, Crosshair, TrendingUp, X, Home, Radio, Sparkles, Settings, Activity, Wifi, WifiOff, Search, Zap, Camera, Loader2, ChevronRight, ChevronLeft, Zap as ZapIcon, RotateCcw, Database, SkipForward, Terminal, ScanLine, LayoutDashboard } from 'lucide-react';
import CodeEntryScreen from './components/CodeEntryScreen';
import CandleChart from './components/CandleChart';
import { calcEMA, calcBollingerBands, calcRSI, calcMACD } from './utils/indicators';
import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { createChart, CandlestickSeries, LineSeries, HistogramSeries, createSeriesMarkers } from 'lightweight-charts';
import { useHistory, useLivePrices, isNSEMarketOpen } from './hooks/useMarketData';
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts';
import SignalsPanel from './SignalsPanel';
import IntroSplash from './IntroSplash';
import HomePanel from './HomePanel';
import PredictionsPanel from './PredictionsPanel';
import StrategySelector from './StrategySelector';
import BacktestRunner from './BacktestRunner';
import { PanelErrorBoundary } from './PanelErrorBoundary';
import CommandPalette from './components/CommandPalette';
import Header from './components/Header';
import TickerBar from './components/TickerBar';
import { describeHttpError } from './utils/apiErrors';
import WatchlistPanel from './components/WatchlistPanel';
import { T, SEED_PRICES, DEFAULT_WATCHLIST, INTERVALS, PRIMARY_TABS, SECONDARY_TABS, MOBILE_TABS, TAB_META, EMPTY_ARRAY, fmt, clr, sign, escapeHTML } from './theme';
import { BRIEF_TIMEOUT_MS, briefErrorMessage } from './utils/briefing';

const TAB_ICONS = { Home, TrendingUp, Radio, Sparkles, Settings };

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
    // Token is already stored in sessionStorage by CodeEntryScreen
    // verifyToken() will pick up the cookie on next apiFetch call
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
      return 'HOME';
    }
    return 'HOME';
  });   // 'HOME' is default

  const [cmdOpen, setCmdOpen] = useState(false);

  const [selected, setSelected] = useState('YESBANK.NS');
  const [ivIdx, setIvIdx]       = useState(0);          // 1D default for intraday
  const [rightTab, setRightTab] = useState('STRATEGIES');
  
  const [drawMode, setDrawMode] = useState(null); // 'SUPPORT' | 'RESISTANCE' | 'TREND' | 'FIB' | null
  const [chartLines, setChartLines] = useState(() => {
    const saved = localStorage.getItem('apex_chart_lines');
    return saved ? JSON.parse(saved) : {};
  }); // { 'SYMBOL.NS': [{price, type, id, p1, p2}] }
  
  const [tradeMarkers, setTradeMarkers] = useState({});
  const [selectedStrategy, setSelectedStrategy] = useState('intraday_momentum');
  const [backtestResults, setBacktestResults] = useState(null);
  
  const [trendStart, setTrendStart] = useState(null); // { time, price } for trend line first click
  const [fibStart, setFibStart] = useState(null); // { time, price } for fib first click
  
  const handleDrawComplete = useCallback((line) => {
    setChartLines(prev => {
      const updated = {
        ...prev,
        [selected]: [...(prev[selected] || []), line]
      };
      localStorage.setItem('apex_chart_lines', JSON.stringify(updated));
      return updated;
    });
    setDrawMode(null);
    setTrendStart(null);
    setFibStart(null);
  }, [selected]);
  
  const handleRemoveLine = useCallback((symbol, lineId) => {
    setChartLines(prev => {
      const updated = {
        ...prev,
        [symbol]: (prev[symbol] || []).filter(l => l.id !== lineId)
      };
      localStorage.setItem('apex_chart_lines', JSON.stringify(updated));
      return updated;
    });
  }, []);
  
  // Server warming/cold start splash page state
  const [serverWarming, setServerWarming] = useState(() => localStorage.getItem('apex_splash_shown') === null);
  // Returning users skip the splash, so backendReady must start true for them or
  // briefing/stats never fetch (they were gated on loggedIn && backendReady).
  const [backendReady, setBackendReady] = useState(() => localStorage.getItem('apex_splash_shown') !== null);

  const symbols = DEFAULT_WATCHLIST.map(w => w.symbol);
  const { prices = {}, connected, dataSource } = useLivePrices(symbols);
  const iv = INTERVALS[ivIdx];
  const currentPrice     = prices?.[selected]?.price ?? SEED_PRICES[selected] ?? 0;
  const hasRealTick      = !!prices?.[selected];
  const currentChangePct = prices?.[selected]?.changePct ?? 0;

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

      // Legacy global shortcuts (delegated to useKeyboardShortcuts hook)
      if (e.key === 'b' || e.key === 'B') { setView('HOME'); }
      else if (e.key === 's' || e.key === 'S') { setView('HOME'); }
      else if (e.key >= '1' && e.key <= '6') {
        const idx = parseInt(e.key) - 1;
        if (idx < INTERVALS.length) { setIvIdx(idx); setView('CHART'); }
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

  // Global keyboard shortcuts hook
  useKeyboardShortcuts({
    enabled: loggedIn && !cmdOpen,
    onBuy: () => showToast('Buy order placed (demo)', 'info'),
    onSell: () => showToast('Sell order placed (demo)', 'info'),
    onTimeframeChange: (tf) => { setIvIdx(INTERVALS.indexOf(tf)); setView('CHART'); },
    onCycleSymbol: (reverse) => {
      const currentIndex = DEFAULT_WATCHLIST.findIndex(w => w.symbol === selected);
      const nextIndex = reverse
        ? (currentIndex - 1 + DEFAULT_WATCHLIST.length) % DEFAULT_WATCHLIST.length
        : (currentIndex + 1) % DEFAULT_WATCHLIST.length;
      setSelected(DEFAULT_WATCHLIST[nextIndex].symbol);
    },
    onFocusSearch: () => setCmdOpen(true),
    onToggleBot: () => setView('HOME'),
    onToggleChart: () => setView('CHART'),
  });

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
          body: JSON.stringify({ symbols: DEFAULT_WATCHLIST.map(w=>w.symbol), interval: '15m', capital: 1840 })
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
  }, []);

  // Mobile layout sub-tab for Chart page
  const [mobileSubTab, setMobileSubTab] = useState('CHART');

  // Console active tab state
  const [consoleTab, setConsoleTab] = useState('CHART');

  // Reference for prices to prevent unnecessary re-fetches in AI effects
  const pricesRef = useRef(prices);
  useEffect(() => {
    pricesRef.current = prices;
  }, [prices]);

  // App-level Cache for Daily Market Briefing & Stats
  const [marketBrief, setMarketBrief] = useState(null);
  const [loadingBrief, setLoadingBrief] = useState(true);
  const [briefError, setBriefError] = useState(null);
  const briefAbortRef = useRef(null);
  const [predictionStats, setPredictionStats] = useState(null);
  const [refreshAnalystToken, setRefreshAnalystToken] = useState(0);

  const fetchMarketBrief = useCallback(() => {
    if (!loggedIn || !backendReady) return;
    if (briefAbortRef.current) briefAbortRef.current.abort();
    const controller = new AbortController();
    briefAbortRef.current = controller;
    setBriefError(null);
    setLoadingBrief(true);
    const timeout = setTimeout(() => controller.abort(), BRIEF_TIMEOUT_MS);
    apiFetch('/api/market_brief', { signal: controller.signal })
    .then(res => res.ok ? res.json() : Promise.reject(new Error(`HTTP ${res.status}`)))
    .then(data => {
      if (briefAbortRef.current !== controller) return;
      setMarketBrief(data);
      setLoadingBrief(false);
    })
    .catch(err => {
      if (briefAbortRef.current !== controller) return;
      setBriefError(briefErrorMessage(err));
      setLoadingBrief(false);
    })
    .finally(() => clearTimeout(timeout));
  }, [loggedIn, backendReady]);

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
  const [aiRecommendationSource, setAiRecommendationSource] = useState('');
  const [aiRecommendationError, setAiRecommendationError] = useState(null);
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
        // Chart lines cleared
        showToast('Chart annotations cleared', 'info');
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

    const cached = aiRecommendationCache.current[selected];
    if (cached && !isManualRefresh) {
      setAiRecommendation(cached.reply);
      setAiRecommendationSource(cached.source || '');
      setAiRecommendationError(null);
      setAiRecommendationLoading(false);
      return;
    }

    let active = true;
    setAiRecommendationLoading(true);
    setAiRecommendation('');
    setAiRecommendationSource('');
    setAiRecommendationError(null);
    
    const timer = setTimeout(async () => {
      try {
        const cleanedSymbol = selected.replace('.NS', '');
        const currentPrices = pricesRef.current || {};
        const feedQuote = currentPrices[selected];
        // Only quote real feed ticks in the AI prompt — seeded fallback prices
        // would present synthetic numbers to the model as "current price".
        const livePrice = feedQuote?.price;
        const pct = feedQuote?.changePct ?? 0;
        const priceClause = livePrice != null
          ? ` at current price ₹${livePrice} (${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%)`
          : '';

        const res = await apiFetch('/api/chat/chart', {
          method: 'POST',
          body: JSON.stringify({
            message: `Provide a quick 1-2 sentence technical analyst recommendation for ${cleanedSymbol}${priceClause}. Focus on technical metrics like RSI, key levels, or potential triggers. Keep it extremely concise.`,
            context: { symbol: cleanedSymbol, price: livePrice ?? null, changePct: pct },
            history: []
          })
        });
        if (res.ok && active) {
          const data = await res.json();
          // Cache only successful responses — errors are never cached, so the
          // next selection or manual refresh hits the backend again.
          aiRecommendationCache.current[selected] = { reply: data.reply, source: data.source || '' };
          setAiRecommendationSource(data.source || '');
          setAiRecommendation(data.reply);
        } else if (active) {
          throw new Error(`HTTP ${res.status}`);
        }
      } catch (err) {
        if (active) {
          // Recommendation lives in dedicated error state; never written to
          // the response cache.
          setAiRecommendation('');
          setAiRecommendationSource('');
          setAiRecommendationError(describeHttpError(err, 'AI recommendation'));
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
            background: T.surfaceDim,
            borderBottom: `1px solid ${T.border}`,
            color: T.gold,
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
            <span style={{ display: 'inline-block', width: 12, height: 12, border: `2px solid ${T.border}`, borderTopColor: T.gold, borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
            CONNECTING TO QUANT SERVER...
          </div>
        )}

        {/* Header */}
        <Header 
          connected={connected} 
          view={view} 
          onViewChange={setView} 
          isMobile={isMobile}
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
                onViewChange={setView} 
                onSelectSymbol={setSelected}
                brief={marketBrief}
                loadingBrief={loadingBrief}
                briefError={briefError}
                stats={predictionStats}
                onRefreshBrief={fetchMarketBrief}
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
              <SignalsPanel onSelectSymbol={handleSignalSelect} selectedSymbol={selected} prices={prices} />
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
          ) : view === 'STRATEGIES' ? (
            /* STRATEGIES VIEW — full width */
            <div className="panel-transition" style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
              <div style={{ flex: 1, padding: 16, overflow: 'auto' }}>
                <StrategySelector
                  selectedStrategy={selectedStrategy}
                  onSelectStrategy={setSelectedStrategy}
                  performanceData={backtestResults?.performance}
                />
                <BacktestRunner onResults={setBacktestResults} />
              </div>
              {isMobile && (
                <div style={{ display: 'flex', borderTop: `1px solid ${T.border}`, background: T.panelAlt, flexShrink: 0, paddingBottom: 'env(safe-area-inset-bottom)' }}>
                  <MobileNavButtons view={view} onChange={setView} />
                </div>
              )}
            </div>
          ) : view === 'CHART' ? (
            /* CHART VIEW — full width with right panel tabs */
            <div className="panel-transition" style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
              <div style={{ display: 'flex', flex: 1, overflow: 'hidden', flexDirection: 'column' }}>
                {/* Chart Area */}
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
                  <div style={{ flex: 1, display: 'flex', minHeight: 0, position: 'relative' }}>
                    {/* Main Chart */}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <CandleChart 
                        symbol={selected} 
                        interval={iv.interval} 
                        range={iv.range} 
                        indicators={indicators} 
                        livePrice={currentPrice} 
                        markers={[]}
                        onLastBarUpdate={handleLastBarUpdate} 
                        drawMode={drawMode} 
                        onDrawComplete={handleDrawComplete} 
                        customLines={chartLines[selected] || []}
                        botPaperMode={true}
                        dataSource={dataSource}
                        trendStart={trendStart}
                        setTrendStart={setTrendStart}
                        fibStart={fibStart}
                        setFibStart={setFibStart}
                      />
                    </div>

                    {/* Right Panel — Chart, Strategies, Backtest, AI Analyst */}
                    <div style={{ 
                      width: isMobile ? '100%' : 420, 
                      minWidth: isMobile ? 0 : 380,
                      maxWidth: isMobile ? '100%' : 420,
                      background: T.surface, 
                      borderLeft: `1px solid ${T.border}`, 
                      display: isMobile ? 'none' : 'flex', 
                      flexDirection: 'column', 
                      overflow: 'hidden' 
                    }}>
                      {/* Right Panel Tab Bar */}
                      <div style={{ 
                        display: 'flex', 
                        background: T.panelAlt, 
                        borderBottom: `1px solid ${T.border}`, 
                        flexShrink: 0,
                        overflowX: 'auto'
                      }}>
                        {['CHART', 'STRATEGIES', 'BACKTEST', 'AI_ANALYST'].map(tab => (
                          <button
                            key={tab}
                            onClick={() => setRightTab(tab)}
                            style={{
                              flex: 1, padding: '10px 12px', border: 'none', cursor: 'pointer',
                              background: 'transparent',
                              color: rightTab === tab ? T.accent : T.textDim,
                              fontSize: 10, fontWeight: 700,
                              fontFamily: "'Inter', sans-serif",
                              borderBottom: `2px solid ${rightTab === tab ? T.accent : 'transparent'}`,
                              marginTop: -1,
                              whiteSpace: 'nowrap'
                            }}
                          >
                            {tab === 'CHART' ? 'CHART' : tab === 'STRATEGIES' ? 'STRATEGIES' : tab === 'BACKTEST' ? 'BACKTEST' : 'AI ANALYST'}
                          </button>
                        ))}
                      </div>

                      {/* Right Panel Content */}
                      <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
                        {rightTab === 'CHART' && (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                            <h3 style={{ fontSize: 12, fontWeight: 700, color: T.text, letterSpacing: '0.04em' }}>INDICATORS</h3>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                              {[
                                ['ema9', 'EMA 9'], ['ema21', 'EMA 21'], ['bb', 'Bollinger Bands'], ['rsi', 'RSI (14)'], ['macd', 'MACD'],
                              ].map(([key, label]) => {
                                const active = indicators[key];
                                return (
                                  <button key={key} onClick={() => setIndicators(prev => ({ ...prev, [key]: !prev[key] }))} style={{
                                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                                    padding: '8px 12px', border: `1px solid ${active ? T.accent : T.border}`,
                                    borderRadius: 6, cursor: 'pointer', fontSize: 11, fontWeight: 600,
                                    background: active ? T.accentDim : 'transparent',
                                    color: active ? T.accentAlt : T.textDim,
                                    fontFamily: "'Inter', sans-serif",
                                    transition: 'all 0.15s'
                                  }}>
                                    <span>{label}</span>
                                    <span style={{ width: 10, height: 10, borderRadius: 2, background: active ? T.accent : T.border }} />
                                  </button>
                                );
                              })}
                            </div>
                          </div>
                        )}

                        {rightTab === 'STRATEGIES' && (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                            <h3 style={{ fontSize: 12, fontWeight: 700, color: T.text, letterSpacing: '0.04em' }}>PREDICTION ENGINES</h3>
                            <StrategySelector
                              selectedStrategy={selectedStrategy}
                              onSelectStrategy={setSelectedStrategy}
                              performanceData={backtestResults?.performance}
                            />
                          </div>
                        )}

                        {rightTab === 'BACKTEST' && (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                            <h3 style={{ fontSize: 12, fontWeight: 700, color: T.text, letterSpacing: '0.04em' }}>BACKTEST</h3>
                            <BacktestRunner onResults={setBacktestResults} />
                          </div>
                        )}

                        {rightTab === 'AI_ANALYST' && (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                              <h3 style={{ fontSize: 12, fontWeight: 700, color: T.text, letterSpacing: '0.04em', margin: 0 }}>AI ANALYST</h3>
                              <button
                                onClick={() => setRefreshAnalystToken(prev => prev + 1)}
                                disabled={aiRecommendationLoading}
                                style={{
                                  padding: '6px 12px', borderRadius: 6, cursor: 'pointer',
                                  background: aiRecommendationLoading ? T.border : T.accent,
                                  border: 'none', color: aiRecommendationLoading ? T.textDim : T.text,
                                  fontSize: 10, fontWeight: 700,
                                  fontFamily: "'Inter', sans-serif",
                                }}
                              >
                                {aiRecommendationLoading ? (
                                  <>
                                    <Loader2 size={12} style={{ animation: 'spin 1s linear infinite' }} />
                                    <span style={{ marginLeft: 6 }}>REFRESH</span>
                                  </>
                                ) : 'REFRESH'}
                              </button>
                            </div>
                            {aiRecommendationError && (
                              <div style={{ 
                                background: T.redDim, 
                                border: `1px solid ${T.red}`, 
                                borderRadius: 8, 
                                padding: 12,
                                color: T.red,
                                fontSize: 11 
                              }}>
                                {aiRecommendationError}
                              </div>
                            )}
                            {aiRecommendation && !aiRecommendationLoading && (
                              <div style={{ 
                                background: T.panel, 
                                border: `1px solid ${T.borderHi}`, 
                                borderRadius: 8, 
                                padding: 12,
                                fontSize: 12,
                                lineHeight: 1.6,
                                color: T.text 
                              }}>
                                {aiRecommendation}
                                {aiRecommendationSource && (
                                  <div style={{ marginTop: 8, fontSize: 10, color: T.textMid }}>
                                    Source: {aiRecommendationSource}
                                  </div>
                                )}
                              </div>
                            )}
                            {!aiRecommendation && !aiRecommendationLoading && !aiRecommendationError && (
                              <div style={{ color: T.textDim, fontSize: 11, fontStyle: 'italic' }}>
                                Click REFRESH to generate an AI technical read for {selected.replace('.NS', '')}.
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Mobile: Right Panel as bottom sheet */}
                  {isMobile && (
                    <div style={{ 
                      background: T.surface, 
                      borderTop: `1px solid ${T.border}`, 
                      maxHeight: '60vh',
                      display: 'flex', 
                      flexDirection: 'column',
                      overflow: 'hidden'
                    }}>
                      <div style={{ 
                        display: 'flex', 
                        background: T.panelAlt, 
                        borderBottom: `1px solid ${T.border}`, 
                        flexShrink: 0,
                        overflowX: 'auto'
                      }}>
                        {['CHART', 'STRATEGIES', 'BACKTEST', 'AI_ANALYST'].map(tab => (
                          <button
                            key={tab}
                            onClick={() => setRightTab(tab)}
                            style={{
                              flex: 1, padding: '10px 12px', border: 'none', cursor: 'pointer',
                              background: 'transparent',
                              color: rightTab === tab ? T.accent : T.textDim,
                              fontSize: 10, fontWeight: 700,
                              fontFamily: "'Inter', sans-serif",
                              borderBottom: `2px solid ${rightTab === tab ? T.accent : 'transparent'}`,
                              marginTop: -1,
                              whiteSpace: 'nowrap'
                            }}
                          >
                            {tab === 'CHART' ? 'CHART' : tab === 'STRATEGIES' ? 'STRATEGIES' : tab === 'BACKTEST' ? 'BACKTEST' : 'AI ANALYST'}
                          </button>
                        ))}
                      </div>
                      <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
                        {rightTab === 'CHART' && (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                            {[
                              ['ema9', 'EMA 9'], ['ema21', 'EMA 21'], ['bb', 'Bollinger Bands'], ['rsi', 'RSI (14)'], ['macd', 'MACD'],
                            ].map(([key, label]) => {
                              const active = indicators[key];
                              return (
                                <button key={key} onClick={() => setIndicators(prev => ({ ...prev, [key]: !prev[key] }))} style={{
                                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                                  padding: '8px 12px', border: `1px solid ${active ? T.accent : T.border}`,
                                  borderRadius: 6, cursor: 'pointer', fontSize: 11, fontWeight: 600,
                                  background: active ? T.accentDim : 'transparent',
                                  color: active ? T.accentAlt : T.textDim,
                                  fontFamily: "'Inter', sans-serif",
                                  transition: 'all 0.15s'
                                }}>
                                  <span>{label}</span>
                                  <span style={{ width: 10, height: 10, borderRadius: 2, background: active ? T.accent : T.border }} />
                                </button>
                              );
                            })}
                          </div>
                        )}

                        {rightTab === 'STRATEGIES' && (
                          <StrategySelector
                            selectedStrategy={selectedStrategy}
                            onSelectStrategy={setSelectedStrategy}
                            performanceData={backtestResults?.performance}
                          />
                        )}

                        {rightTab === 'BACKTEST' && (
                          <BacktestRunner onResults={setBacktestResults} />
                        )}

                        {rightTab === 'AI_ANALYST' && (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                              <h3 style={{ fontSize: 12, fontWeight: 700, color: T.text, letterSpacing: '0.04em', margin: 0 }}>AI ANALYST</h3>
                              <button
                                onClick={() => setRefreshAnalystToken(prev => prev + 1)}
                                disabled={aiRecommendationLoading}
                                style={{
                                  padding: '6px 12px', borderRadius: 6, cursor: 'pointer',
                                  background: aiRecommendationLoading ? T.border : T.accent,
                                  border: 'none', color: aiRecommendationLoading ? T.textDim : T.text,
                                  fontSize: 10, fontWeight: 700,
                                  fontFamily: "'Inter', sans-serif",
                                }}
                              >
                                {aiRecommendationLoading ? (
                                  <>
                                    <Loader2 size={12} style={{ animation: 'spin 1s linear infinite' }} />
                                    <span style={{ marginLeft: 6 }}>REFRESH</span>
                                  </>
                                ) : 'REFRESH'}
                              </button>
                            </div>
                            {aiRecommendationError && (
                              <div style={{ 
                                background: T.redDim, 
                                border: `1px solid ${T.red}`, 
                                borderRadius: 8, 
                                padding: 12,
                                color: T.red,
                                fontSize: 11 
                              }}>
                                {aiRecommendationError}
                              </div>
                            )}
                            {aiRecommendation && !aiRecommendationLoading && (
                              <div style={{ 
                                background: T.panel, 
                                border: `1px solid ${T.borderHi}`, 
                                borderRadius: 8, 
                                padding: 12,
                                fontSize: 12,
                                lineHeight: 1.6,
                                color: T.text 
                              }}>
                                {aiRecommendation}
                                {aiRecommendationSource && (
                                  <div style={{ marginTop: 8, fontSize: 10, color: T.textMid }}>
                                    Source: {aiRecommendationSource}
                                  </div>
                                )}
                              </div>
                            )}
                            {!aiRecommendation && !aiRecommendationLoading && !aiRecommendationError && (
                              <div style={{ color: T.textDim, fontSize: 11, fontStyle: 'italic' }}>
                                Click REFRESH to generate an AI technical read for {selected.replace('.NS', '')}.
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {isMobile && (
                  <div style={{ display: 'flex', borderTop: `1px solid ${T.border}`, background: T.panelAlt, flexShrink: 0, paddingBottom: 'env(safe-area-inset-bottom)' }}>
                    <MobileNavButtons view={view} onChange={setView} />
                  </div>
                )}
              </div>
            </div>
          ) : (
            /* Fallback - redirect to HOME */
            <div className="panel-transition" style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: T.textDim }}>
                Redirecting to Home...
              </div>
            </div>
          )}

        </div>
        <CommandPalette 
          isOpen={cmdOpen} 
          onClose={() => setCmdOpen(false)} 
          onAction={handleCommandAction}
          onViewChange={setView}
          selectedSymbol={selected}
          prices={prices}
        />
        </div>
      )}
    </>
  );
}