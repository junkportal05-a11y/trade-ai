/**
 * PerformancePanel.jsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Full-width Backtesting & Live Signal History Dashboard.
 * Includes a dynamic Historical Backtest Sandbox with interactive charting.
 */

import React, { useState, useEffect, useCallback } from "react";

const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const T = {
  bg:       '#080a0f',
  surface:  '#0d1018',
  panel:    '#111520',
  border:   '#1a1f2e',
  borderHi: '#252c40',
  text:     '#d0d8ed',
  textMid:  '#6e7a96',
  textDim:  '#363d55',
  green:    '#00e5a8',
  greenDim: 'rgba(0,229,168,0.1)',
  red:      '#ff3d5a',
  redDim:   'rgba(255,61,90,0.1)',
  blue:     '#4da6ff',
  blueDim:  'rgba(77,166,255,0.1)',
  gold:     '#f5c842',
  goldDim:  'rgba(245,200,66,0.1)',
  accent:   '#7b6cff',
  accentDim:'rgba(123,108,255,0.12)',
  gray:     '#404863',
  grayDim:  'rgba(64,72,99,0.2)',
};

const fmt = (n, d = 2) => n == null ? '—' : Number(n).toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d });
const pct  = (n) => n == null ? '—' : `${n > 0 ? '+' : ''}${Number(n).toFixed(2)}%`;
const clr  = (v) => v > 0 ? T.green : v < 0 ? T.red : T.textMid;
const mono = { fontFamily: "'IBM Plex Mono', monospace" };

const STATUS_META = {
  HIT_TARGET: { label: 'TARGET HIT',  bg: T.greenDim, color: T.green,   dot: T.green  },
  HIT_STOP:   { label: 'STOP HIT',    bg: T.redDim,   color: T.red,     dot: T.red    },
  PENDING:    { label: 'ACTIVE',       bg: T.goldDim,  color: T.gold,    dot: T.gold   },
  EXPIRED:    { label: 'EXPIRED',      bg: T.grayDim,  color: T.gray,    dot: T.gray   },
  CLOSED:     { label: 'CLOSED',       bg: T.blueDim,  color: T.blue,    dot: T.blue   },
};

const WATCHLIST_STOCKS = [
  { symbol: 'RELIANCE.NS', name: 'Reliance Industries' },
  { symbol: 'TCS.NS', name: 'TCS' },
  { symbol: 'HDFCBANK.NS', name: 'HDFC Bank' },
  { symbol: 'INFY.NS', name: 'Infosys' },
  { symbol: 'ICICIBANK.NS', name: 'ICICI Bank' },
  { symbol: 'SBIN.NS', name: 'State Bank of India' },
  { symbol: 'TATAMOTORS.NS', name: 'Tata Motors' },
  { symbol: 'WIPRO.NS', name: 'Wipro' },
  { symbol: 'AXISBANK.NS', name: 'Axis Bank' }
];

function StatusBadge({ status }) {
  const m = STATUS_META[status] || STATUS_META.CLOSED;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      padding: '2px 8px', borderRadius: 4,
      background: m.bg, color: m.color,
      fontSize: 9, fontWeight: 700, letterSpacing: '0.08em',
      fontFamily: "'IBM Plex Mono', monospace",
    }}>
      <span style={{ width: 5, height: 5, borderRadius: '50%', background: m.dot,
        animation: status === 'PENDING' ? 'pulse 2s infinite' : 'none' }} />
      {m.label}
    </span>
  );
}

function KpiCard({ label, value, sub, color, big }) {
  return (
    <div style={{
      background: T.panel, border: `1px solid ${T.border}`,
      borderRadius: 10, padding: '14px 18px', flex: 1, minWidth: 120,
    }}>
      <div style={{ fontSize: 9, color: T.textDim, letterSpacing: '0.12em',
        fontFamily: "'IBM Plex Mono', monospace", marginBottom: 8 }}>{label}</div>
      <div style={{ fontSize: big ? 24 : 18, fontWeight: 700,
        color: color || T.text, fontFamily: "'IBM Plex Mono', monospace",
        letterSpacing: '-0.02em', lineHeight: 1 }}>{value}</div>
      {sub && <div style={{ fontSize: 9.5, color: T.textMid, marginTop: 6 }}>{sub}</div>}
    </div>
  );
}

function WinBar({ label, wins, total, avg_pnl }) {
  const rate = total > 0 ? (wins / total) * 100 : 0;
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ fontSize: 11, color: T.text, fontFamily: "'IBM Plex Mono', monospace" }}>
          {label}
        </span>
        <span style={{ fontSize: 10, color: T.textMid, fontFamily: "'IBM Plex Mono', monospace" }}>
          {wins}/{total} · {rate.toFixed(0)}%
          {avg_pnl != null && (
            <span style={{ color: clr(avg_pnl), marginLeft: 8 }}>avg {pct(avg_pnl)}</span>
          )}
        </span>
      </div>
      <div style={{ height: 6, background: T.border, borderRadius: 3, overflow: 'hidden' }}>
        <div style={{
          height: '100%', width: `${rate}%`,
          background: rate >= 60 ? T.green : rate >= 40 ? T.gold : T.red,
          borderRadius: 3, transition: 'width 0.8s ease',
        }} />
      </div>
    </div>
  );
}

// Glowing SVG-based Equity Curve component with premium interactive cursor + tooltip
function EquityChart({ data }) {
  if (!data || data.length < 2) return null;
  const values = data.map(d => d.value);
  const minVal = Math.min(...values);
  const maxVal = Math.max(...values);
  const valRange = maxVal - minVal || 1;
  const initialVal = values[0] || 10000;
  
  const width = 500;
  const height = 100;
  const padding = 8;
  
  // State for hover tracking
  const [hoveredIndex, setHoveredIndex] = useState(null);
  const svgRef = React.useRef(null);
  
  const points = data.map((d, i) => {
    const x = padding + (i / (data.length - 1)) * (width - 2 * padding);
    const y = height - padding - ((d.value - minVal) / valRange) * (height - 2 * padding);
    return { x, y, val: d.value, date: d.date, index: i };
  });
  
  const pathD = `M ${points.map(p => `${p.x},${p.y}`).join(' L ')}`;
  const areaD = `${pathD} L ${width - padding},${height - padding} L ${padding},${height - padding} Z`;

  const handleMouseMove = (e) => {
    if (!svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const mouseX = ((e.clientX - rect.left) / rect.width) * width;
    
    // Find closest point by x coordinate
    let closestIndex = 0;
    let minDiff = Infinity;
    points.forEach((p, idx) => {
      const diff = Math.abs(p.x - mouseX);
      if (diff < minDiff) {
        minDiff = diff;
        closestIndex = idx;
      }
    });
    setHoveredIndex(closestIndex);
  };

  const handleMouseLeave = () => {
    setHoveredIndex(null);
  };

  const activePoint = hoveredIndex !== null ? points[hoveredIndex] : null;
  const currentReturnPct = activePoint ? ((activePoint.val - initialVal) / initialVal * 100).toFixed(2) : 0;
  
  return (
    <div style={{ marginTop: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, color: T.textDim, fontFamily: "'IBM Plex Mono', monospace", marginBottom: 4 }}>
        <span>CAPITAL HISTORY (EQUITY CURVE)</span>
        <span>PEAK: ₹{fmt(maxVal)} · TROUGH: ₹{fmt(minVal)}</span>
      </div>
      
      {/* Interactive Tooltip HUD */}
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between', 
        padding: '6px 10px', 
        background: T.panel, 
        border: `1px solid ${T.borderHi}`, 
        borderRadius: '6px 6px 0 0', 
        fontSize: 9.5, 
        color: T.textMid, 
        ...mono,
        borderBottom: 'none',
        height: '28px'
      }}>
        {activePoint ? (
          <>
            <span>DATE: <span style={{ color: T.text, fontWeight: 700 }}>{activePoint.date}</span></span>
            <span>EQUITY: <span style={{ color: T.accent, fontWeight: 700 }}>₹{fmt(activePoint.val)}</span></span>
            <span>RETURN: <span style={{ color: clr(activePoint.val - initialVal), fontWeight: 700 }}>{activePoint.val >= initialVal ? '+' : ''}{currentReturnPct}%</span></span>
          </>
        ) : (
          <div style={{ color: T.textDim, fontSize: 8.5 }}>💡 Move mouse over the chart below to track capital history</div>
        )}
      </div>

      <svg 
        ref={svgRef}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        viewBox={`0 0 ${width} ${height}`} 
        style={{ 
          width: '100%', 
          height: '80px', 
          background: 'rgba(255,255,255,0.005)', 
          borderRadius: '0 0 8px 8px', 
          border: `1px solid ${T.border}`, 
          display: 'block',
          cursor: 'crosshair'
        }}
      >
        <defs>
          <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={T.accent} stopOpacity="0.18"/>
            <stop offset="100%" stopColor={T.accent} stopOpacity="0.0"/>
          </linearGradient>
        </defs>
        
        {/* Horizontal half-way gridline */}
        <line x1={padding} y1={height/2} x2={width-padding} y2={height/2} stroke={T.border} strokeDasharray="3,3" />
        
        {/* Area fill */}
        <path d={areaD} fill="url(#areaGrad)" />
        
        {/* Sparkline curve */}
        <path d={pathD} fill="none" stroke={T.accent} strokeWidth="1.5" />
        
        {/* Interactive tracking elements */}
        {activePoint && (
          <>
            {/* Vertical crosshair tracker */}
            <line 
              x1={activePoint.x} 
              y1={padding} 
              x2={activePoint.x} 
              y2={height - padding} 
              stroke={T.borderHi} 
              strokeWidth="0.8" 
              strokeDasharray="2,2" 
            />
            {/* Glowing active point dot */}
            <circle 
              cx={activePoint.x} 
              cy={activePoint.y} 
              r="4" 
              fill={T.accent} 
              stroke="#fff" 
              strokeWidth="1"
              style={{ filter: 'drop-shadow(0px 0px 3px rgba(123,108,255,0.8))' }}
            />
            <circle 
              cx={activePoint.x} 
              cy={activePoint.y} 
              r="8" 
              fill={T.accent} 
              fillOpacity="0.25"
            />
          </>
        )}
      </svg>
    </div>
  );
}

export default function PerformancePanel() {
  const [stats,   setStats]   = useState(null);
  const [history, setHistory] = useState([]);
  const [filter,  setFilter]  = useState('ALL');
  const [loading, setLoading] = useState(true);
  const [resetting, setResetting] = useState(false);

  // Historical Backtesting Sandbox State
  const [backtestSymbol, setBacktestSymbol]   = useState('RELIANCE.NS');
  const [backtestRange, setBacktestRange]     = useState('3mo');
  const [backtestCap, setBacktestCap]         = useState('10000');
  const [backtestStopAtr, setBacktestStopAtr]   = useState(3.0); // Optimized default
  const [backtestTargetAtr, setBacktestTargetAtr] = useState(2.0); // Optimized default
  const [backtestEntryScore, setBacktestEntryScore] = useState(7); // Optimized default
  const [backtestRiskPct, setBacktestRiskPct]     = useState(2.0);
  const [backtestEarlyExit, setBacktestEarlyExit] = useState(-4); // Optimized default
  const [showConfig, setShowConfig]               = useState(false);
  const [backtestResult, setBacktestResult]   = useState(null);
  const [backtestLoading, setBacktestLoading] = useState(false);
  const [backtestError, setBacktestError]     = useState(null);

  // Trade Journal State
  const [journalEntries, setJournalEntries] = useState([]);
  const [jSymbol, setJSymbol] = useState('RELIANCE.NS');
  const [jDir, setJDir] = useState('BUY');
  const [jPrice, setJPrice] = useState('');
  const [jQty, setJQty] = useState('');
  const [jReason, setJReason] = useState('');
  const [jEmotion, setJEmotion] = useState('Calm');
  const [jSubmitting, setJSubmitting] = useState(false);

  const fetchJournal = useCallback(async () => {
    try {
      const headers = { 'X-Session-Token': sessionStorage.getItem('apt_token') || '' };
      const res = await fetch(`${BASE}/api/journal`, { headers });
      if (res.ok) {
        setJournalEntries(await res.json());
      }
    } catch (e) {
      console.error("Failed to load journal:", e);
    }
  }, []);

  const handleCreateJournal = async (e) => {
    e.preventDefault();
    const price = parseFloat(jPrice);
    const qty = parseInt(jQty);
    if (!jSymbol || isNaN(price) || isNaN(qty) || qty <= 0 || price <= 0) {
      alert("Please fill in all journal fields correctly!");
      return;
    }
    setJSubmitting(true);
    try {
      const headers = {
        'Content-Type': 'application/json',
        'X-Session-Token': sessionStorage.getItem('apt_token') || ''
      };
      const entry = {
        symbol: jSymbol,
        direction: jDir,
        entry_price: price,
        qty: qty,
        reason: jReason,
        emotion: jEmotion,
        status: 'OPEN'
      };
      const res = await fetch(`${BASE}/api/journal`, {
        method: 'POST',
        headers,
        body: JSON.stringify(entry)
      });
      if (res.ok) {
        setJPrice('');
        setJQty('');
        setJReason('');
        setJEmotion('Calm');
        await fetchJournal();
      }
    } catch (e) {
      console.error("Failed to log journal:", e);
    } finally {
      setJSubmitting(false);
    }
  };

  const handleDeleteJournal = async (id) => {
    if (!confirm("Are you sure you want to delete this journal entry?")) return;
    try {
      const headers = { 'X-Session-Token': sessionStorage.getItem('apt_token') || '' };
      const res = await fetch(`${BASE}/api/journal/${id}`, {
        method: 'DELETE',
        headers
      });
      if (res.ok) {
        await fetchJournal();
      }
    } catch (e) {
      console.error("Failed to delete journal entry:", e);
    }
  };

  const load = useCallback(async () => {
    try {
      const headers = { 'X-Session-Token': sessionStorage.getItem('apt_token') || '' };
      const [sRes, hRes] = await Promise.all([
        fetch(`${BASE}/api/backtest/stats`, { headers }),
        fetch(`${BASE}/api/backtest/history?limit=200`, { headers }),
      ]);
      if (sRes.ok) setStats(await sRes.json());
      if (hRes.ok) {
        const d = await hRes.json();
        setHistory(d.history || []);
      }
      fetchJournal();
    } catch {
      // backend offline
    } finally {
      setLoading(false);
    }
  }, [fetchJournal]);

  useEffect(() => {
    load();
    const t = setInterval(load, 25000); // refresh every 25s
    return () => clearInterval(t);
  }, [load]);

  const reset = async () => {
    if (!confirm("Clear all signal history? This cannot be undone.")) return;
    setResetting(true);
    try {
      await fetch(`${BASE}/api/backtest/reset`, {
        method: 'POST',
        headers: { 'X-Admin-Key': 'apextrade_admin_2024_secure' }
      });
      await load();
    } finally {
      setResetting(false);
    }
  };

  const handleRunBacktest = async () => {
    const capitalAmt = parseFloat(backtestCap.replace(/,/g, ''));
    if (!capitalAmt || capitalAmt < 500) {
      setBacktestError("Minimum capital of ₹500 required for simulation");
      return;
    }

    setBacktestLoading(true);
    setBacktestError(null);
    setBacktestResult(null);

    try {
      const query = `symbol=${backtestSymbol}&range=${backtestRange}&capital=${capitalAmt}&stop_atr=${backtestStopAtr}&target_atr=${backtestTargetAtr}&entry_score=${backtestEntryScore}&risk_pct=${backtestRiskPct}&early_exit=${backtestEarlyExit}`;
      const res = await fetch(`${BASE}/api/backtest/run?${query}`, {
        headers: { 'X-Session-Token': sessionStorage.getItem('apt_token') || '' }
      });
      if (!res.ok) throw new Error(`HTTP Error ${res.status}`);
      const data = await res.json();
      if (data.error) {
        setBacktestError(data.error);
      } else {
        setBacktestResult(data);
      }
    } catch (e) {
      setBacktestError("Backend not responding. Make sure uvicorn backend server is running.");
    } finally {
      setBacktestLoading(false);
    }
  };

  const filtered = filter === 'ALL' ? history : history.filter(h => h.status === filter);
  const noData = !stats || stats.total === 0;

  if (loading) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
        gap: 12, color: T.textMid, fontFamily: "'IBM Plex Mono', monospace", fontSize: 12 }}>
        <span style={{ width: 14, height: 14, border: `2px solid ${T.border}`,
          borderTopColor: T.accent, borderRadius: '50%', display: 'inline-block',
          animation: 'spin 0.7s linear infinite' }} />
        LOADING PERFORMANCE DATABASE
      </div>
    );
  }

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px',
      display: 'flex', flexDirection: 'column', gap: 20, background: T.bg }}>

      {/* ── SECTION 1: HISTORICAL BACKTEST SANDBOX ── */}
      <div style={{ background: T.panel, border: `1px solid ${T.border}`, borderRadius: 12, padding: '16px 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
          <span style={{ fontSize: 16 }}>🚀</span>
          <span style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.1em', color: T.text, fontFamily: "'IBM Plex Mono', monospace" }}>
            HISTORICAL STRATEGY BACKTESTING SANDBOX
          </span>
          <span style={{ fontSize: 8.5, padding: '2px 6px', borderRadius: 3, background: T.greenDim, color: T.green, ...mono, border: `1px solid ${T.green}30` }}>
            1D DAILY BARS
          </span>
        </div>
        <div style={{ fontSize: 11, color: T.textMid, lineHeight: 1.5, marginBottom: 14 }}>
          Runs the technical scanning rules (EMA crossovers, ADX choppiness gating, Candlestick Bible hammers/engulfing, and volume surges) over historical data to calculate win rates, maximum drawdown, and profit curves.
        </div>

        {/* Inputs row */}
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center', marginBottom: 14 }}>
          {/* Stock selector */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <span style={{ fontSize: 8, color: T.textDim, ...mono }}>SELECT STOCK</span>
            <select 
              value={backtestSymbol} 
              onChange={e => setBacktestSymbol(e.target.value)}
              style={{ background: T.bg, color: T.text, border: `1px solid ${T.borderHi}`, borderRadius: 6, padding: '8px 12px', fontSize: 11, ...mono, outline: 'none' }}
            >
              {WATCHLIST_STOCKS.map(s => (
                <option key={s.symbol} value={s.symbol}>{s.symbol.replace('.NS','')} - {s.name}</option>
              ))}
            </select>
          </div>

          {/* Timeframe range */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <span style={{ fontSize: 8, color: T.textDim, ...mono }}>RANGE TIMEFRAME</span>
            <select 
              value={backtestRange} 
              onChange={e => setBacktestRange(e.target.value)}
              style={{ background: T.bg, color: T.text, border: `1px solid ${T.borderHi}`, borderRadius: 6, padding: '8px 12px', fontSize: 11, ...mono, outline: 'none' }}
            >
              <option value="1mo">1 Month</option>
              <option value="3mo">3 Months</option>
              <option value="6mo">6 Months</option>
              <option value="1y">1 Year</option>
            </select>
          </div>

          {/* Capital input */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <span style={{ fontSize: 8, color: T.textDim, ...mono }}>SIMULATED CAPITAL (₹)</span>
            <input 
              value={backtestCap} 
              onChange={e => setBacktestCap(e.target.value)}
              placeholder="Capital size..."
              style={{ background: T.bg, color: T.text, border: `1px solid ${T.borderHi}`, borderRadius: 6, padding: '8px 12px', fontSize: 11, fontWeight: 700, ...mono, outline: 'none', width: '120px' }}
            />
          </div>

          {/* Config toggle button */}
          <button 
            onClick={() => setShowConfig(!showConfig)}
            style={{
              alignSelf: 'flex-end',
              padding: '8px 14px', background: showConfig ? T.borderHi : 'transparent', border: `1px solid ${T.borderHi}`,
              borderRadius: 6, color: T.text, fontSize: 10, fontWeight: 700,
              cursor: 'pointer', fontFamily: "'IBM Plex Mono', monospace",
              letterSpacing: '0.06em', transition: 'all 0.2s', marginTop: '12px'
            }}
          >
            {showConfig ? '⚙ HIDE SETTINGS' : '⚙ TWEAK STRATEGY'}
          </button>

          {/* Run button */}
          <button 
            onClick={handleRunBacktest} 
            disabled={backtestLoading}
            style={{
              alignSelf: 'flex-end',
              padding: '9px 18px', background: backtestLoading ? T.accentDim : T.accent, border: 'none',
              borderRadius: 6, color: '#fff', fontSize: 10, fontWeight: 700,
              cursor: backtestLoading ? 'not-allowed' : 'pointer', fontFamily: "'IBM Plex Mono', monospace",
              letterSpacing: '0.06em', transition: 'all 0.2s', marginTop: '12px'
            }}
          >
            {backtestLoading ? '⚙ RUNNING...' : '🚀 RUN BACKTEST'}
          </button>
        </div>

        {/* Collapsible Strategy settings drawer */}
        {showConfig && (
          <div style={{ 
            background: T.bg, 
            border: `1px solid ${T.borderHi}`, 
            borderRadius: 8, 
            padding: '14px 18px', 
            marginBottom: 14, 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
            gap: 16,
            animation: 'fadeIn 0.2s ease'
          }}>
            {/* Risk per trade */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 8.5, color: T.textMid, ...mono }}>
                <span>RISK PER TRADE</span>
                <span style={{ color: T.accent, fontWeight: 700 }}>{backtestRiskPct}%</span>
              </div>
              <input 
                type="range" min="0.5" max="5.0" step="0.5"
                value={backtestRiskPct}
                onChange={e => setBacktestRiskPct(parseFloat(e.target.value))}
                style={{ accentColor: T.accent, cursor: 'pointer' }}
              />
              <span style={{ fontSize: 7.5, color: T.textDim }}>Golden rule: 1-2% maximum account exposure.</span>
            </div>

            {/* Entry score gate */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 8.5, color: T.textMid, ...mono }}>
                <span>ENTRY SCORE THRESHOLD</span>
                <span style={{ color: T.green, fontWeight: 700 }}>+{backtestEntryScore}</span>
              </div>
              <input 
                type="range" min="3" max="8" step="1"
                value={backtestEntryScore}
                onChange={e => setBacktestEntryScore(parseInt(e.target.value))}
                style={{ accentColor: T.green, cursor: 'pointer' }}
              />
              <span style={{ fontSize: 7.5, color: T.textDim }}>Minimum points from EMAs/ADX/volume to enter.</span>
            </div>

            {/* Stop loss ATR */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 8.5, color: T.textMid, ...mono }}>
                <span>STOP-LOSS DISTANCE (ATR)</span>
                <span style={{ color: T.red, fontWeight: 700 }}>{backtestStopAtr}x ATR</span>
              </div>
              <input 
                type="range" min="1.0" max="3.0" step="0.1"
                value={backtestStopAtr}
                onChange={e => setBacktestStopAtr(parseFloat(e.target.value))}
                style={{ accentColor: T.red, cursor: 'pointer' }}
              />
              <span style={{ fontSize: 7.5, color: T.textDim }}>Wider stops allow volatile stocks to breathe.</span>
            </div>

            {/* Take profit ATR */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 8.5, color: T.textMid, ...mono }}>
                <span>PROFIT TARGET DISTANCE (ATR)</span>
                <span style={{ color: T.gold, fontWeight: 700 }}>{backtestTargetAtr}x ATR</span>
              </div>
              <input 
                type="range" min="1.5" max="5.0" step="0.1"
                value={backtestTargetAtr}
                onChange={e => setBacktestTargetAtr(parseFloat(e.target.value))}
                style={{ accentColor: T.gold, cursor: 'pointer' }}
              />
              <span style={{ fontSize: 7.5, color: T.textDim }}>Set targets to achieve &gt; 1:2 Reward-to-Risk.</span>
            </div>

            {/* Early exit threshold */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 8.5, color: T.textMid, ...mono }}>
                <span>EARLY EXIT THRESHOLD</span>
                <span style={{ color: T.blue, fontWeight: 700 }}>{backtestEarlyExit}</span>
              </div>
              <input 
                type="range" min="-6" max="-1" step="1"
                value={backtestEarlyExit}
                onChange={e => setBacktestEarlyExit(parseInt(e.target.value))}
                style={{ accentColor: T.blue, cursor: 'pointer' }}
              />
              <span style={{ fontSize: 7.5, color: T.textDim }}>Lower values (e.g. -4) filter out minor pullbacks.</span>
            </div>
          </div>
        )}

        {/* Errors display */}
        {backtestError && (
          <div style={{ padding: '9px 14px', background: T.redDim, border: `1px solid rgba(255,61,90,0.25)`, borderRadius: 6, fontSize: 10, color: T.red, ...mono }}>
            ⚠ Error running backtest: {backtestError}
          </div>
        )}

        {/* Backtest Results Render */}
        {backtestResult && (
          <div style={{ borderTop: `1px solid ${T.border}`, paddingTop: 14, animation: 'fadeIn 0.3s ease', display: 'flex', flexDirection: 'column', gap: 14 }}>
            {/* KPI Cards */}
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <KpiCard 
                label="STRATEGY WIN RATE" 
                value={`${backtestResult.win_rate}%`} 
                sub={`${backtestResult.wins} Wins / ${backtestResult.losses} Losses`} 
                color={backtestResult.win_rate >= 50 ? T.green : backtestResult.win_rate >= 35 ? T.gold : T.red}
                big
              />
              <KpiCard 
                label="TOTAL RETURN (P&L)" 
                value={`${backtestResult.total_pnl >= 0 ? '+' : ''}₹${fmt(backtestResult.total_pnl)}`} 
                sub={`${backtestResult.total_pnl_pct}% return on capital`} 
                color={clr(backtestResult.total_pnl)}
              />
              <KpiCard 
                label="PROFIT FACTOR" 
                value={backtestResult.profit_factor} 
                sub="Gross profit / Gross loss ratio" 
                color={backtestResult.profit_factor >= 1.5 ? T.green : backtestResult.profit_factor >= 1.0 ? T.gold : T.red}
              />
              <KpiCard 
                label="MAX HISTORICAL DRAWDOWN" 
                value={`${backtestResult.max_drawdown}%`} 
                sub="Maximum peak-to-trough drop" 
                color={backtestResult.max_drawdown <= 5 ? T.green : backtestResult.max_drawdown <= 12 ? T.gold : T.red}
              />
              <KpiCard 
                label="TOTAL EXECUTED TRADES" 
                value={backtestResult.total_trades} 
                sub={`Simulated over ${backtestResult.period === '1y' ? '1 year' : backtestResult.period === '6mo' ? '6 months' : '3 months'}`} 
              />
            </div>

            {/* Sparkline Equity Chart */}
            <EquityChart data={backtestResult.equity_curve} />

            {/* Simulated closed trades list */}
            <div>
              <div style={{ fontSize: 9, color: T.textMid, fontFamily: "'IBM Plex Mono', monospace", marginBottom: 6 }}>
                SIMULATED TRADES LOG ({backtestResult.trades.length})
              </div>
              <div style={{ maxHeight: '180px', overflowY: 'auto', border: `1px solid ${T.border}`, borderRadius: 8 }}>
                {/* Headers */}
                <div style={{ display: 'grid', gridTemplateColumns: '70px 140px 65px 65px 75px 130px', padding: '6px 14px', borderBottom: `1px solid ${T.border}`, fontSize: 7.5, color: T.textDim, ...mono, letterSpacing: '0.08em' }}>
                  <span>TRADE DATES</span>
                  <span>EXIT STATUS</span>
                  <span>BUY PRICE</span>
                  <span>SELL PRICE</span>
                  <span>TRADE P&L</span>
                  <span>EXIT REASON</span>
                </div>
                {/* Rows */}
                {backtestResult.trades.length === 0 ? (
                  <div style={{ padding: 20, textAlign: 'center', fontSize: 10, color: T.textDim, ...mono }}>No trades executed during this timeframe.</div>
                ) : (
                  backtestResult.trades.map((t, index) => (
                    <div key={index} style={{ display: 'grid', gridTemplateColumns: '70px 140px 65px 65px 75px 130px', padding: '8px 14px', borderBottom: index === backtestResult.trades.length - 1 ? 'none' : `1px solid ${T.border}`, fontSize: 10, ...mono, color: T.textMid }}>
                      <span style={{ fontSize: 9 }}>{t.entry_date}</span>
                      <span style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                        <span style={{ width: 4, height: 4, borderRadius: '50%', background: t.pnl > 0 ? T.green : t.pnl < 0 ? T.red : T.textDim }} />
                        <span style={{ fontSize: 8.5, fontWeight: 700, color: t.pnl > 0 ? T.green : t.pnl < 0 ? T.red : T.textMid }}>{t.status}</span>
                      </span>
                      <span>₹{fmt(t.entry_price, 1)}</span>
                      <span>₹{fmt(t.exit_price, 1)}</span>
                      <span style={{ color: clr(t.pnl), fontWeight: 700 }}>{t.pnl_pct > 0 ? '+' : ''}{t.pnl_pct}%</span>
                      <span style={{ fontSize: 9, color: T.textDim, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{t.reason}</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── SECTION 2: LIVE PAPER TRADING SIGNAL LOGS ── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: `1px solid ${T.border}`, paddingTop: 18 }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, color: T.text,
            fontFamily: "'IBM Plex Mono', monospace", letterSpacing: '0.04em' }}>
            Live Signal & Paper Trading History
          </div>
          <div style={{ fontSize: 10.5, color: T.textMid, marginTop: 4 }}>
            Tracks signals logged in real-time from the background scanning daemon during market hours.
          </div>
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <button onClick={reset} disabled={resetting || noData} style={{
            padding: '8px 16px', background: T.redDim, border: `1px solid rgba(255,61,90,0.3)`,
            borderRadius: 6, color: T.red, fontSize: 10, fontWeight: 700,
            cursor: noData ? 'not-allowed' : 'pointer', opacity: noData ? 0.4 : 1,
            fontFamily: "'IBM Plex Mono', monospace", letterSpacing: '0.06em',
            transition: 'all 0.2s',
          }}>
            {resetting ? 'CLEARING...' : '⟳ RESET DATABASE'}
          </button>
        </div>
      </div>

      {noData ? (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center',
          justifyContent: 'center', gap: 16, padding: '40px 0' }}>
          <div style={{ fontSize: 32 }}>📡</div>
          <div style={{ fontSize: 13, fontWeight: 700, color: T.text,
            fontFamily: "'IBM Plex Mono', monospace" }}>NO TRADES LOGGED YET</div>
          <div style={{ fontSize: 11, color: T.textMid, textAlign: 'center', maxWidth: 400, lineHeight: 1.6 }}>
            The background scanner logs BUY/SELL signals automatically every 60 seconds
            during NSE market hours (9:15 AM – 3:30 PM IST). Check back after the market opens.
          </div>
        </div>
      ) : (
        <>
          {/* KPI Cards */}
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <KpiCard
              label="WIN RATE"
              value={`${stats.win_rate}%`}
              sub={`${stats.won} wins / ${stats.lost} losses`}
              color={stats.win_rate >= 60 ? T.green : stats.win_rate >= 40 ? T.gold : T.red}
              big
            />
            <KpiCard label="TOTAL SIGNALS" value={stats.total}
              sub={`${stats.pending} active`} />
            <KpiCard label="AVG P&L" value={pct(stats.avg_pnl)}
              color={clr(stats.avg_pnl)} sub="per resolved trade" />
            <KpiCard label="RESOLVED" value={stats.resolved}
              sub={`${stats.expired} expired · ${stats.closed} closed`} />
          </div>

          {/* Breakdown charts */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            {/* By sector */}
            <div style={{ background: T.panel, border: `1px solid ${T.border}`,
              borderRadius: 10, padding: '16px 20px' }}>
              <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.12em',
                color: T.textMid, fontFamily: "'IBM Plex Mono', monospace", marginBottom: 16 }}>
                WIN RATE BY SECTOR
              </div>
              {stats.by_sector.length === 0
                ? <div style={{ color: T.textDim, fontSize: 11 }}>No resolved trades yet</div>
                : stats.by_sector.map(s => (
                    <WinBar key={s.sector} label={s.sector}
                      wins={s.wins} total={s.total} />
                  ))
              }
            </div>

            {/* By direction */}
            <div style={{ background: T.panel, border: `1px solid ${T.border}`,
              borderRadius: 10, padding: '16px 20px' }}>
              <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.12em',
                color: T.textMid, fontFamily: "'IBM Plex Mono', monospace", marginBottom: 16 }}>
                WIN RATE BY DIRECTION
              </div>
              {stats.by_direction.length === 0
                ? <div style={{ color: T.textDim, fontSize: 11 }}>No resolved trades yet</div>
                : stats.by_direction.map(d => (
                    <WinBar key={d.direction} label={d.direction}
                      wins={d.wins} total={d.total} avg_pnl={d.avg_pnl} />
                  ))
              }

              {/* P&L summary */}
              <div style={{ marginTop: 20, paddingTop: 16, borderTop: `1px solid ${T.border}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <div style={{ textAlign: 'center', flex: 1 }}>
                    <div style={{ fontSize: 18, fontWeight: 700, color: T.green,
                      fontFamily: "'IBM Plex Mono', monospace" }}>{stats.won}</div>
                    <div style={{ fontSize: 9, color: T.textDim, marginTop: 4 }}>WINS</div>
                  </div>
                  <div style={{ textAlign: 'center', flex: 1 }}>
                    <div style={{ fontSize: 18, fontWeight: 700, color: T.red,
                      fontFamily: "'IBM Plex Mono', monospace" }}>{stats.lost}</div>
                    <div style={{ fontSize: 9, color: T.textDim, marginTop: 4 }}>LOSSES</div>
                  </div>
                  <div style={{ textAlign: 'center', flex: 1 }}>
                    <div style={{ fontSize: 18, fontWeight: 700, color: T.gray,
                      fontFamily: "'IBM Plex Mono', monospace" }}>{stats.expired}</div>
                    <div style={{ fontSize: 9, color: T.textDim, marginTop: 4 }}>EXPIRED</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Signal history table */}
          <div style={{ background: T.panel, border: `1px solid ${T.border}`, borderRadius: 10 }}>
            {/* Table header */}
            <div style={{ padding: '14px 20px', borderBottom: `1px solid ${T.border}`,
              display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.12em',
                color: T.textMid, fontFamily: "'IBM Plex Mono', monospace" }}>
                SIGNAL LOG ({filtered.length})
              </span>
              {/* Filter tabs */}
              <div style={{ display: 'flex', gap: 4 }}>
                {['ALL','PENDING','HIT_TARGET','HIT_STOP','EXPIRED','CLOSED'].map(f => (
                  <button key={f} onClick={() => setFilter(f)} style={{
                    padding: '3px 10px', borderRadius: 4, border: 'none',
                    background: filter === f ? T.accentDim : 'transparent',
                    color: filter === f ? T.accent : T.textDim,
                    fontSize: 8, fontWeight: 700, cursor: 'pointer',
                    fontFamily: "'IBM Plex Mono', monospace", letterSpacing: '0.06em',
                    transition: 'all 0.15s',
                  }}>{f === 'ALL' ? 'ALL' : (STATUS_META[f]?.label || f)}</button>
                ))}
              </div>
            </div>

            {/* Column headers */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: '90px 80px 70px 80px 80px 80px 70px 80px 100px',
              padding: '8px 20px', borderBottom: `1px solid ${T.border}`,
              fontSize: 8, color: T.textDim, letterSpacing: '0.1em',
              fontFamily: "'IBM Plex Mono', monospace",
            }}>
              {['SYMBOL','DIRECTION','CONF','ENTRY','TARGET','STOP','EXIT','P&L','STATUS'].map(h => (
                <span key={h}>{h}</span>
              ))}
            </div>

            {/* Rows */}
            <div style={{ maxHeight: 300, overflowY: 'auto' }}>
              {filtered.length === 0 ? (
                <div style={{ padding: '30px 20px', textAlign: 'center',
                  color: T.textDim, fontSize: 11, fontFamily: "'IBM Plex Mono', monospace" }}>
                  NO SIGNALS MATCH THIS FILTER
                </div>
              ) : filtered.map(row => (
                <div key={row.id} style={{
                  display: 'grid',
                  gridTemplateColumns: '90px 80px 70px 80px 80px 80px 70px 80px 100px',
                  padding: '10px 20px',
                  borderBottom: `1px solid ${T.border}`,
                  fontSize: 11,
                  fontFamily: "'IBM Plex Mono', monospace",
                  transition: 'background 0.1s',
                  cursor: 'default',
                }}
                  onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.02)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                >
                  <span style={{ color: T.text, fontWeight: 700, fontSize: 11 }}>
                    {row.symbol.replace('.NS','')}
                  </span>
                  <span style={{ color: row.signal_type.includes('BUY') ? T.green : T.red,
                    fontSize: 10, fontWeight: 700 }}>
                    {row.signal_type}
                  </span>
                  <span style={{ color: row.confidence >= 70 ? T.green : row.confidence >= 55 ? T.gold : T.textMid }}>
                    {row.confidence}%
                  </span>
                  <span style={{ color: T.textMid }}>₹{row.entry_price?.toFixed(1)}</span>
                  <span style={{ color: T.green }}>₹{row.target?.toFixed(1)}</span>
                  <span style={{ color: T.red }}>₹{row.stop_loss?.toFixed(1)}</span>
                  <span style={{ color: T.textMid }}>
                    {row.exit_price ? `₹${row.exit_price.toFixed(1)}` : '—'}
                  </span>
                  <span style={{ color: clr(row.pnl_pct), fontWeight: row.pnl_pct ? 700 : 400 }}>
                    {row.pnl_pct != null ? pct(row.pnl_pct) : '—'}
                  </span>
                  <StatusBadge status={row.status} />
                </div>
              ))}
            </div>
          </div>

          {/* ── SECTION 3: PERSISTENT TRADING JOURNAL ── */}
          <div style={{ marginTop: 32, borderTop: `1px solid ${T.border}`, paddingTop: 24 }}>
            <h3 style={{ fontSize: 13, fontWeight: 700, color: T.accent, letterSpacing: '0.04em', marginBottom: 16 }}>
              📓 PERSISTENT TRADING JOURNAL
            </h3>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 24 }}>
              
              {/* Left Column: Form */}
              <form onSubmit={handleCreateJournal} style={{ background: T.panel, border: `1px solid ${T.border}`, borderRadius: 10, padding: 18, display: 'flex', flexDirection: 'column', gap: 14, height: 'fit-content' }}>
                <div style={{ fontSize: 10, fontWeight: 700, color: T.textMid, borderBottom: `1px solid ${T.border}`, paddingBottom: 8, marginBottom: 4 }}>
                  LOG A NEW TRANSACTION
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                    <label style={{ fontSize: 9, color: T.textDim }}>SYMBOL</label>
                    <select value={jSymbol} onChange={e => setJSymbol(e.target.value)} style={{ background: T.bg, border: `1px solid ${T.borderHi}`, borderRadius: 6, color: T.text, padding: 6, fontSize: 11, outline: 'none' }}>
                      {WATCHLIST_STOCKS.map(s => (
                        <option key={s.symbol} value={s.symbol}>{s.symbol.replace('.NS','')}</option>
                      ))}
                    </select>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                    <label style={{ fontSize: 9, color: T.textDim }}>DIRECTION</label>
                    <select value={jDir} onChange={e => setJDir(e.target.value)} style={{ background: T.bg, border: `1px solid ${T.borderHi}`, borderRadius: 6, color: T.text, padding: 6, fontSize: 11, outline: 'none' }}>
                      <option value="BUY">BUY (LONG)</option>
                      <option value="SELL">SELL (SHORT)</option>
                    </select>
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                    <label style={{ fontSize: 9, color: T.textDim }}>ENTRY PRICE (₹)</label>
                    <input type="number" step="0.01" value={jPrice} onChange={e => setJPrice(e.target.value)} placeholder="0.00" style={{ background: T.bg, border: `1px solid ${T.borderHi}`, borderRadius: 6, color: T.text, padding: '5px 8px', fontSize: 11, outline: 'none' }} />
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                    <label style={{ fontSize: 9, color: T.textDim }}>QUANTITY</label>
                    <input type="number" value={jQty} onChange={e => setJQty(e.target.value)} placeholder="Shares..." style={{ background: T.bg, border: `1px solid ${T.borderHi}`, borderRadius: 6, color: T.text, padding: '5px 8px', fontSize: 11, outline: 'none' }} />
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                  <label style={{ fontSize: 9, color: T.textDim }}>EMOTIONAL STATE</label>
                  <select value={jEmotion} onChange={e => setJEmotion(e.target.value)} style={{ background: T.bg, border: `1px solid ${T.borderHi}`, borderRadius: 6, color: T.text, padding: 6, fontSize: 11, outline: 'none' }}>
                    <option value="Calm">Calm & Objective</option>
                    <option value="Greedy">Greedy / FOMO</option>
                    <option value="Fearful">Fearful / Anxious</option>
                    <option value="Excited">Excited / Impulsive</option>
                  </select>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                  <label style={{ fontSize: 9, color: T.textDim }}>TRADE RATIONALE (REASON)</label>
                  <textarea rows="3" value={jReason} onChange={e => setJReason(e.target.value)} placeholder="Explain technical confirmation, support levels, pattern details..." style={{ background: T.bg, border: `1px solid ${T.borderHi}`, borderRadius: 6, color: T.text, padding: '6px 8px', fontSize: 11, outline: 'none', resize: 'none', fontFamily: 'inherit' }} />
                </div>

                <button type="submit" disabled={jSubmitting} style={{ background: T.accent, border: 'none', borderRadius: 6, color: '#fff', padding: 10, fontSize: 11, fontWeight: 700, cursor: 'pointer', transition: 'all 0.2s', marginTop: 4 }}>
                  {jSubmitting ? 'LOGGING...' : '📝 SAVE TO JOURNAL'}
                </button>
              </form>

              {/* Right Column: Logs List */}
              <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 10, overflow: 'hidden', display: 'flex', flexDirection: 'column', minHeight: 320 }}>
                <div style={{ padding: '12px 16px', borderBottom: `1px solid ${T.border}`, background: T.panelAlt, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 10, fontWeight: 700, color: T.textMid }}>JOURNALED TRANSACTIONS LOG ({journalEntries.length})</span>
                  <span style={{ fontSize: 8, color: T.textDim }}>PERSISTENT SQLite STORAGE</span>
                </div>
                
                <div style={{ flex: 1, overflowY: 'auto', maxHeight: 380 }}>
                  {journalEntries.length === 0 ? (
                    <div style={{ padding: 40, textAlign: 'center', color: T.textDim, fontSize: 11 }}>
                      No journaled trades yet. Log your first transaction using the form on the left.
                    </div>
                  ) : (
                    journalEntries.map(entry => (
                      <div key={entry.id} style={{ padding: '12px 16px', borderBottom: `1px solid ${T.border}`, display: 'flex', justifyContent: 'space-between', gap: 16 }}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, flex: 1 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <span style={{ fontSize: 12, fontWeight: 700, color: '#fff', ...mono }}>{entry.symbol}</span>
                            <span style={{ fontSize: 9, fontWeight: 700, color: entry.direction === 'BUY' ? T.green : T.red, background: entry.direction === 'BUY' ? T.greenDim : T.redDim, padding: '1px 5px', borderRadius: 3 }}>
                              {entry.direction}
                            </span>
                            <span style={{ fontSize: 9, color: T.textDim, ...mono }}>{entry.entry_date.split(' ')[0]}</span>
                          </div>
                          {entry.reason && (
                            <div style={{ fontSize: 11, color: T.textMid, lineHeight: 1.4, margin: '4px 0' }}>
                              &ldquo;{entry.reason}&rdquo;
                            </div>
                          )}
                          <div style={{ display: 'flex', gap: 12, fontSize: 10 }}>
                            <span style={{ color: T.textDim }}>Size: <span style={{ color: T.text, fontWeight: 600 }}>{entry.qty}</span></span>
                            <span style={{ color: T.textDim }}>Price: <span style={{ color: T.text, fontWeight: 600 }}>₹{fmt(entry.entry_price)}</span></span>
                            <span style={{ color: T.textDim }}>Emotion: <span style={{ 
                              color: entry.emotion === 'Greedy' ? T.gold : entry.emotion === 'Fearful' ? T.red : entry.emotion === 'Excited' ? T.blue : T.green,
                              fontWeight: 600 
                            }}>{entry.emotion}</span></span>
                          </div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center' }}>
                          <button
                            onClick={() => handleDeleteJournal(entry.id)}
                            style={{ background: 'rgba(255,61,90,0.05)', border: `1px solid rgba(255,61,90,0.2)`, borderRadius: 4, color: T.red, padding: '4px 8px', fontSize: 9, fontWeight: 700, cursor: 'pointer', transition: 'all 0.15s' }}
                            onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,61,90,0.15)'}
                            onMouseLeave={e => e.currentTarget.style.background = 'rgba(255,61,90,0.05)'}
                          >
                            DELETE
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

            </div>
          </div>
        </>
      )}
    </div>
  );
}
