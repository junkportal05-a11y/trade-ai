/**
 * ScannerPanel.jsx
 * Unified NSE Smart Scanner — merges signal scanning with capital allocation
 * into one seamless, responsive view.
 *
 * Layout (top → bottom):
 *  1. Header row — title, scan-type badge, market-bias badge, RESCAN button
 *  2. Capital input bar — preset buttons + custom input (inline, compact)
 *  3. Profit summary banner — shown only when capital is entered AND allocations exist
 *  4. Filter bar — ALL / BUY / WEAK BUY / HOLD / WEAK SELL / SELL
 *  5. Signal cards — each card includes optional allocation section when capital is set
 *  6. Disclaimer
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';

/* ─── Base URL ──────────────────────────────────────────────────────────────── */
const BASE = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:8000`;

/* ─── Design Tokens ─────────────────────────────────────────────────────────── */
const T = {
  bg:         '#080a0f',
  surface:    '#0d1018',
  panel:      '#111520',
  panelAlt:   '#0f1219',
  border:     '#1a1f2e',
  borderHi:   '#252c40',
  text:       '#d0d8ed',
  textMid:    '#6e7a96',
  textDim:    '#363d55',
  green:      '#00e5a8',
  greenDim:   'rgba(0,229,168,0.1)',
  greenGlow:  'rgba(0,229,168,0.3)',
  red:        '#ff3d5a',
  redDim:     'rgba(255,61,90,0.1)',
  redGlow:    'rgba(255,61,90,0.3)',
  gold:       '#f5c842',
  goldDim:    'rgba(245,200,66,0.1)',
  blue:       '#4da6ff',
  blueDim:    'rgba(77,166,255,0.1)',
  accent:     '#7b6cff',
  accentAlt:  '#9b5de5',
  accentDim:  'rgba(123,108,255,0.12)',
  accentGlow: 'rgba(123,108,255,0.25)',
};

/* ─── Signal Config ─────────────────────────────────────────────────────────── */
const SIGNAL_CFG = {
  'BUY':       { color: T.green,   bg: T.greenDim,                          glow: T.greenGlow,                      icon: '▲', label: 'BUY'       },
  'WEAK BUY':  { color: '#7bdb9e', bg: 'rgba(123,219,158,0.08)',            glow: 'rgba(123,219,158,0.2)',           icon: '△', label: 'WEAK BUY'  },
  'HOLD':      { color: T.gold,    bg: T.goldDim,                           glow: 'rgba(245,200,66,0.2)',            icon: '◆', label: 'HOLD'      },
  'WEAK SELL': { color: '#ff9a7b', bg: 'rgba(255,154,123,0.08)',            glow: 'rgba(255,154,123,0.2)',           icon: '▽', label: 'WEAK SELL' },
  'SELL':      { color: T.red,     bg: T.redDim,                            glow: T.redGlow,                         icon: '▼', label: 'SELL'      },
};

/* ─── Formatters ────────────────────────────────────────────────────────────── */
const fmt   = (n, d = 2) => n == null ? '—' : Number(n).toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d });
const fmtPct = (n) => n == null ? '—' : `${n > 0 ? '+' : ''}${Number(n).toFixed(2)}%`;
const fmtINR = (n) => {
  if (n == null || isNaN(n)) return '—';
  if (n >= 1e7) return `₹${(n / 1e7).toFixed(2)}Cr`;
  if (n >= 1e5) return `₹${(n / 1e5).toFixed(2)}L`;
  if (n >= 1e3) return `₹${(n / 1e3).toFixed(1)}K`;
  return `₹${Number(n).toFixed(0)}`;
};
const mono = { fontFamily: "'IBM Plex Mono', monospace" };
const sans = { fontFamily: "'Inter', sans-serif" };

/* ─── Capital Presets ───────────────────────────────────────────────────────── */
const PRESETS = [
  { label: '₹500',  value: 500    },
  { label: '₹1K',   value: 1000   },
  { label: '₹2K',   value: 2000   },
  { label: '₹5K',   value: 5000   },
  { label: '₹10K',  value: 10000  },
  { label: '₹25K',  value: 25000  },
  { label: '₹50K',  value: 50000  },
  { label: '₹1L',   value: 100000 },
];

/* ─── Scan Progress Steps ───────────────────────────────────────────────────── */
const SCAN_STEPS = [
  "Fetching live NSE OHLCV data...",
  "Screening high-volatility stocks...",
  "Computing RSI momentum signals...",
  "Running MACD crossover detection...",
  "Checking VWAP & EMA alignment...",
  "Running Supertrend filter...",
  "Detecting volume surges...",
  "Scoring by volatility × confidence...",
  "Applying position sizing rules...",
  "Building high-return plan...",
];

/* ─── CSS Keyframes (injected once) ─────────────────────────────────────────── */
const KEYFRAMES_ID = '__scanner_panel_keyframes__';
if (typeof document !== 'undefined' && !document.getElementById(KEYFRAMES_ID)) {
  const style = document.createElement('style');
  style.id = KEYFRAMES_ID;
  style.textContent = `
    @keyframes sp_spin   { to { transform: rotate(360deg); } }
    @keyframes sp_pulse  { 0%,100% { opacity:1; } 50% { opacity:0.4; } }
    @keyframes sp_fadeIn { from { opacity:0; transform:translateY(6px); } to { opacity:1; transform:translateY(0); } }
  `;
  document.head.appendChild(style);
}

/* ═══════════════════════════════════════════════════════════════════════════════
   SUB-COMPONENTS
   ═══════════════════════════════════════════════════════════════════════════════ */

/* ── Countdown Timer ────────────────────────────────────────────────────────── */
function Countdown({ target, onFire }) {
  const [secs, setSecs] = useState(Math.max(0, Math.floor((target - Date.now()) / 1000)));
  useEffect(() => {
    const t = setInterval(() => {
      const s = Math.max(0, Math.floor((target - Date.now()) / 1000));
      setSecs(s);
      if (s === 0) onFire();
    }, 1000);
    return () => clearInterval(t);
  }, [target, onFire]);
  const m = Math.floor(secs / 60), s = secs % 60;
  return (
    <span style={{ ...mono, fontSize: 10, color: secs < 60 ? T.gold : T.textDim }}>
      {String(m).padStart(2, '0')}:{String(s).padStart(2, '0')}
    </span>
  );
}

/* ── Technical Indicator Badge ──────────────────────────────────────────────── */
function Badge({ label, value, color }) {
  return (
    <span style={{
      display: 'inline-flex', gap: 4, alignItems: 'center',
      padding: '2px 7px', borderRadius: 4,
      background: `${color}15`, border: `1px solid ${color}30`,
      fontSize: 9, ...mono,
    }}>
      <span style={{ color: T.textDim }}>{label}</span>
      <span style={{ color }}>{value}</span>
    </span>
  );
}

/* ── Confidence Bar ─────────────────────────────────────────────────────────── */
function ConfBar({ confidence, signal }) {
  const cfg = SIGNAL_CFG[signal] || SIGNAL_CFG['HOLD'];
  return (
    <div style={{ marginTop: 6 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
        <span style={{ fontSize: 9, color: T.textDim, ...mono }}>CONFIDENCE</span>
        <span style={{ fontSize: 9, color: cfg.color, fontWeight: 700, ...mono }}>{confidence}%</span>
      </div>
      <div style={{ height: 3, background: T.border, borderRadius: 2, overflow: 'hidden' }}>
        <div style={{
          height: '100%',
          width: `${confidence}%`,
          background: `linear-gradient(90deg, ${cfg.color}80, ${cfg.color})`,
          borderRadius: 2,
          transition: 'width 0.8s ease',
          boxShadow: `0 0 6px ${cfg.glow}`,
        }} />
      </div>
    </div>
  );
}

/* ── Scan Progress Animation ────────────────────────────────────────────────── */
function ScanProgress({ elapsed }) {
  const step = Math.min(Math.floor(elapsed / 10), SCAN_STEPS.length - 1);
  const pct  = Math.min(97, (elapsed / 110) * 100);
  return (
    <div style={{
      background: T.panel, border: `1px solid ${T.border}`,
      borderRadius: 10, padding: 16, display: 'flex', flexDirection: 'column', gap: 12,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        <div style={{ position: 'relative', width: 38, height: 38, flexShrink: 0 }}>
          <div style={{ position: 'absolute', inset: 0, borderRadius: '50%', border: `3px solid ${T.border}` }} />
          <div style={{ position: 'absolute', inset: 0, borderRadius: '50%', border: '3px solid transparent', borderTopColor: T.accent, animation: 'sp_spin 0.9s linear infinite' }} />
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14 }}>🔍</div>
        </div>
        <div>
          <div style={{ fontSize: 12, fontWeight: 700, color: T.text, ...mono }}>DEEP MARKET ANALYSIS</div>
          <div style={{ fontSize: 10, color: T.textMid, marginTop: 2 }}>
            {elapsed}s — scanning high-volatility NSE stocks for best entries
          </div>
        </div>
      </div>

      <div>
        <div style={{ height: 6, background: T.border, borderRadius: 3, overflow: 'hidden' }}>
          <div style={{
            height: '100%', width: `${pct}%`,
            background: `linear-gradient(90deg, ${T.accent}, ${T.green})`,
            borderRadius: 3, transition: 'width 1.2s ease',
          }} />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4, fontSize: 9, color: T.textDim, ...mono }}>
          <span>{SCAN_STEPS[step]}</span>
          <span>{Math.floor(pct)}%</span>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 3 }}>
        {['RSI (14)', 'MACD (12/26/9)', 'EMA 9/21/50', 'Bollinger Bands',
          'VWAP', 'Supertrend', 'Volume Surge', 'ATR Sizing'].map((ind, i) => {
          const done = elapsed >= (i + 1) * 11;
          return (
            <div key={ind} style={{
              display: 'flex', gap: 6, alignItems: 'center',
              fontSize: 9, ...mono,
              color: done ? T.green : T.textDim, transition: 'color 0.5s',
            }}>
              <span style={{ fontSize: 10 }}>{done ? '✓' : '·'}</span>
              {ind}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ── Filter Bar ─────────────────────────────────────────────────────────────── */
function FilterBar({ filter, onFilter, count }) {
  const filters = ['ALL', 'BUY', 'WEAK BUY', 'HOLD', 'WEAK SELL', 'SELL'];
  return (
    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', padding: '10px 16px', borderBottom: `1px solid ${T.border}`, alignItems: 'center' }}>
      {filters.map(f => {
        const cfg = f === 'ALL' ? { color: T.accent, bg: T.accentDim } : (SIGNAL_CFG[f] || { color: T.textMid, bg: 'transparent' });
        const active = filter === f;
        return (
          <button key={f} onClick={() => onFilter(f)} style={{
            padding: '4px 10px', borderRadius: 4,
            border: `1px solid ${active ? cfg.color + '60' : T.border}`,
            background: active ? cfg.bg : 'transparent',
            color: active ? cfg.color : T.textDim,
            fontSize: 9, fontWeight: 700, cursor: 'pointer', ...mono,
            letterSpacing: '0.06em', transition: 'all 0.15s',
          }}>
            {f === 'ALL' ? `ALL (${count})` : f}
          </button>
        );
      })}
    </div>
  );
}

/* ── Signal Card (with optional allocation section) ─────────────────────────── */
function SignalCard({ sig, onSelect, isSelected, livePriceData, allocation }) {
  const cfg = SIGNAL_CFG[sig.signal] || SIGNAL_CFG['HOLD'];
  const isBull = sig.signal.includes('BUY');
  const isBear = sig.signal.includes('SELL');

  const currentPrice = livePriceData?.price ?? sig.price;

  let liveReturnPct = 0;
  if (currentPrice && sig.entry && (isBull || isBear)) {
    liveReturnPct = isBull
      ? ((currentPrice - sig.entry) / sig.entry) * 100
      : ((sig.entry - currentPrice) / sig.entry) * 100;
  }

  const pnlColor = liveReturnPct > 0 ? T.green : liveReturnPct < 0 ? T.red : T.textMid;
  const pnlValue = (isBull || isBear)
    ? `${liveReturnPct > 0 ? '+' : ''}${liveReturnPct.toFixed(2)}%`
    : '—';

  const pos = allocation; // matched allocation position for this symbol

  return (
    <div
      onClick={() => onSelect(sig.symbol)}
      style={{
        background: isSelected ? `${cfg.color}08` : T.panel,
        border: `1px solid ${isSelected ? cfg.color + '50' : T.border}`,
        borderLeft: `3px solid ${cfg.color}`,
        borderRadius: 8,
        padding: '14px 16px',
        cursor: 'pointer',
        transition: 'all 0.2s',
        boxShadow: isSelected ? `0 0 20px ${cfg.glow}` : 'none',
        animation: 'sp_fadeIn 0.3s ease',
      }}
      onMouseEnter={e => !isSelected && (e.currentTarget.style.borderColor = cfg.color + '40')}
      onMouseLeave={e => !isSelected && (e.currentTarget.style.borderColor = T.border)}
    >
      {/* Row 1: Symbol + Signal badge */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 14, fontWeight: 700, color: T.text, ...mono, letterSpacing: '0.03em' }}>
              {sig.symbol.replace('.NS', '')}
            </span>
            <span style={{
              fontSize: 9, color: T.textDim, background: T.surface,
              padding: '2px 6px', borderRadius: 3, border: `1px solid ${T.border}`,
            }}>
              {sig.sector}
            </span>
          </div>
          <div style={{ fontSize: 10, color: T.textDim, marginTop: 2 }}>{sig.name}</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 5,
            padding: '4px 10px', borderRadius: 5,
            background: cfg.bg, border: `1px solid ${cfg.color}30`,
            fontSize: 10, fontWeight: 700, color: cfg.color, ...mono,
            boxShadow: `0 0 12px ${cfg.glow}`,
          }}>
            <span>{cfg.icon}</span>
            <span>{cfg.label}</span>
          </div>
        </div>
      </div>

      {/* Row 2: Prices grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 6, marginBottom: 8 }}>
        {[
          { label: 'ENTRY',   value: `₹${fmt(sig.entry)}`,     color: T.text },
          { label: 'CURRENT', value: `₹${fmt(currentPrice)}`,  color: T.blue, isLive: true },
          { label: 'TARGET',  value: `₹${fmt(sig.target)}`,    color: isBull ? T.green : isBear ? T.red : T.gold },
          { label: 'STOP',    value: `₹${fmt(sig.stop_loss)}`, color: isBull ? T.red : isBear ? T.green : T.textMid },
          { label: 'LIVE P&L', value: pnlValue,                color: pnlColor },
        ].map(({ label, value, color, isLive }) => (
          <div key={label} style={{
            background: T.surface, padding: '6px 8px', borderRadius: 5,
            border: `1px solid ${T.border}`, position: 'relative',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
              <div style={{ fontSize: 8, color: T.textDim, letterSpacing: '0.08em', ...mono }}>{label}</div>
              {isLive && livePriceData && (
                <span style={{
                  display: 'inline-block', width: 4, height: 4, borderRadius: '50%',
                  background: T.green, animation: 'sp_pulse 1.2s infinite',
                }} />
              )}
            </div>
            <div style={{ fontSize: 11, color, fontWeight: 700, ...mono }}>{value}</div>
          </div>
        ))}
      </div>

      {/* Target % badge */}
      <div style={{ marginBottom: 8 }}>
        <span style={{ fontSize: 9, color: isBull ? T.green : isBear ? T.red : T.gold, ...mono }}>
          {fmtPct(sig.target_pct)} target move
        </span>
        <span style={{ fontSize: 9, color: T.textDim, marginLeft: 8 }}>
          ATR: ₹{fmt(sig.atr)}
        </span>
        <span style={{ fontSize: 9, color: T.textDim, marginLeft: 8 }}>
          R:R: 1:{sig.rr_ratio}
        </span>
      </div>

      {/* Indicator badges */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5, marginBottom: 8 }}>
        <Badge label="RSI"  value={sig.rsi}  color={sig.rsi > 70 ? T.red : sig.rsi < 30 ? T.green : sig.rsi > 55 ? '#7bdb9e' : T.textMid} />
        <Badge label="VWAP" value={currentPrice > sig.vwap ? '↑ Above' : '↓ Below'} color={currentPrice > sig.vwap ? T.green : T.red} />
        <Badge label="EMA"  value={sig.ema9 > sig.ema21 ? '9>21 Bull' : '9<21 Bear'} color={sig.ema9 > sig.ema21 ? T.green : T.red} />
        <Badge label="VOL"  value={`${sig.vol_ratio}x`} color={sig.vol_ratio >= 1.5 ? T.blue : sig.vol_ratio < 0.7 ? T.textDim : T.textMid} />
        <Badge label="MACD" value={sig.macd_hist > 0 ? '▲ Bull' : '▼ Bear'} color={sig.macd_hist > 0 ? T.green : T.red} />
      </div>

      {/* Reasoning */}
      {sig.reasoning && (
        <div style={{
          fontSize: 10, color: T.textMid, lineHeight: 1.5,
          padding: '8px 10px', background: T.surface, borderRadius: 5,
          border: `1px solid ${T.border}`, borderLeft: `2px solid ${cfg.color}40`,
        }}>
          {sig.reasoning}
        </div>
      )}

      <ConfBar confidence={sig.confidence} signal={sig.signal} />

      {/* ── Allocation Section (only when capital is entered and allocation matched) ── */}
      {pos && (
        <div style={{
          marginTop: 10, padding: '12px 14px', borderRadius: 7,
          background: T.surface, border: `1px solid ${T.borderHi}`,
          animation: 'sp_fadeIn 0.4s ease',
        }}>
          <div style={{
            fontSize: 9, fontWeight: 700, color: T.accent, letterSpacing: '0.1em',
            ...mono, marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6,
          }}>
            💰 ALLOCATION
          </div>

          {/* Shares / Amount / Profit / Loss / R:R */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 6, marginBottom: 8 }}>
            {[
              { label: 'SHARES',       value: pos.shares,                              color: T.text },
              { label: 'INVEST',       value: fmtINR(pos.amount_invested),             color: T.blue },
              { label: 'TARGET +',     value: `+${fmtINR(pos.potential_profit)}`,       color: T.green },
              { label: 'MAX LOSS',     value: `-${fmtINR(pos.potential_loss)}`,         color: T.red },
              { label: 'R : R',        value: `1:${pos.rr_ratio}`,                     color: T.accent },
            ].map(({ label, value, color }) => (
              <div key={label} style={{
                background: T.panelAlt, padding: '7px 8px', borderRadius: 5,
                border: `1px solid ${T.border}`, textAlign: 'center',
              }}>
                <div style={{ fontSize: 7, color: T.textDim, letterSpacing: '0.1em', ...mono, marginBottom: 3 }}>{label}</div>
                <div style={{ fontSize: 11, fontWeight: 700, color, ...mono }}>{value}</div>
              </div>
            ))}
          </div>

          {/* Why This Stock */}
          {pos.reasons?.length > 0 && (
            <div style={{
              padding: '10px 12px', background: T.bg, borderRadius: 6,
              border: `1px solid ${T.border}`,
            }}>
              <div style={{ fontSize: 8, color: T.textDim, letterSpacing: '0.1em', ...mono, marginBottom: 6 }}>
                WHY THIS STOCK
              </div>
              {pos.reasons.map((r, i) => (
                <div key={i} style={{ display: 'flex', gap: 6, marginBottom: 4, alignItems: 'flex-start' }}>
                  <span style={{ color: T.green, fontSize: 10, flexShrink: 0 }}>✓</span>
                  <span style={{ fontSize: 10, color: T.textMid, lineHeight: 1.5 }}>{r}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════════
   MAIN COMPONENT
   ═══════════════════════════════════════════════════════════════════════════════ */
export default function ScannerPanel({ onSelectSymbol, selectedSymbol, prices, cash }) {
  /* ── Signal state ─────────────────────────────────────────────────────────── */
  const [signals, setSignals]     = useState([]);
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState(null);
  const [scanTime, setScanTime]   = useState(null);
  const [filter, setFilter]       = useState('ALL');
  const [nextScan, setNextScan]   = useState(null);
  const abortRef = useRef(null);

  /* ── Capital / allocation state ───────────────────────────────────────────── */
  const [capital, setCapital]     = useState(cash ? String(cash) : '');
  const [allocPlan, setAllocPlan] = useState(null);
  const [allocLoading, setAllocLoading] = useState(false);
  const [allocElapsed, setAllocElapsed] = useState(0);
  const allocTimerRef = useRef(null);

  const REFRESH_MS = 5 * 60 * 1000; // 5 minutes

  const capitalNum = parseFloat(String(capital).replace(/,/g, '')) || 0;

  /* ── Allocation elapsed timer ─────────────────────────────────────────────── */
  useEffect(() => {
    if (allocLoading) {
      setAllocElapsed(0);
      allocTimerRef.current = setInterval(() => setAllocElapsed(e => e + 1), 1000);
    } else {
      clearInterval(allocTimerRef.current);
    }
    return () => clearInterval(allocTimerRef.current);
  }, [allocLoading]);

  /* ── Fetch allocation helper ──────────────────────────────────────────────── */
  const fetchAllocation = useCallback(async (amt) => {
    if (!amt || amt < 500) return;
    setAllocLoading(true);
    try {
      const res = await fetch(`${BASE}/api/allocate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ capital: amt }),
      });
      if (!res.ok) throw new Error(`Allocate HTTP ${res.status}`);
      const data = await res.json();
      setAllocPlan(data);
    } catch {
      // Allocation failure is non-fatal — signals still show
      setAllocPlan(null);
    } finally {
      setAllocLoading(false);
    }
  }, []);

  /* ── Main scan function ───────────────────────────────────────────────────── */
  const runScan = useCallback(async () => {
    if (abortRef.current) abortRef.current.abort();
    abortRef.current = new AbortController();

    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${BASE}/api/signals`, { signal: abortRef.current.signal });
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      const data = await res.json();
      if (data.signals && data.signals.length > 0) {
        setSignals(data.signals);
      } else {
        setSignals([]);
        setError('Signal engine returned empty results. Backend may still be warming up.');
      }
      setScanTime(data.scan_time);
      setNextScan(Date.now() + REFRESH_MS);
    } catch (e) {
      if (e.name !== 'AbortError') {
        setError(e.message || 'Backend not reachable.');
        setSignals([]);
        setScanTime(null);
        setNextScan(Date.now() + REFRESH_MS);
      }
    } finally {
      setLoading(false);
    }

    // If capital is entered, also fetch allocation
    if (capitalNum >= 500) {
      fetchAllocation(capitalNum);
    }
  }, [capitalNum, fetchAllocation]);

  /* ── Auto-scan on mount ───────────────────────────────────────────────────── */
  useEffect(() => { runScan(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  /* ── Build allocation map (symbol → position) ─────────────────────────────── */
  const allocMap = {};
  if (allocPlan?.positions) {
    for (const pos of allocPlan.positions) {
      // Normalise: backend may return 'RELIANCE' or 'RELIANCE.NS'
      const sym = pos.symbol.includes('.') ? pos.symbol : `${pos.symbol}.NS`;
      allocMap[sym] = pos;
      allocMap[pos.symbol] = pos;
    }
  }

  /* ── Derived data ─────────────────────────────────────────────────────────── */
  const filtered = filter === 'ALL' ? signals : signals.filter(s => s.signal === filter);
  const buys  = signals.filter(s => s.signal === 'BUY' || s.signal === 'WEAK BUY').length;
  const sells = signals.filter(s => s.signal === 'SELL' || s.signal === 'WEAK SELL').length;
  const holds = signals.filter(s => s.signal === 'HOLD').length;
  const marketBias = buys > sells + 2 ? 'BULLISH' : sells > buys + 2 ? 'BEARISH' : 'NEUTRAL';
  const biasColor  = marketBias === 'BULLISH' ? T.green : marketBias === 'BEARISH' ? T.red : T.gold;

  const showProfitBanner = capitalNum > 0 && allocPlan && allocPlan.positions?.length > 0 && !allocLoading;

  /* ── Handle capital preset click ──────────────────────────────────────────── */
  const handlePreset = (val) => {
    setCapital(val.toString());
    setAllocPlan(null);
  };

  /* ── Handle capital submit (re-fetch allocation only) ─────────────────────── */
  const handleCapitalSubmit = () => {
    if (capitalNum >= 500) {
      setAllocPlan(null);
      fetchAllocation(capitalNum);
    }
  };

  /* ═══════════════════════════════════════════════════════════════════════════
     RENDER
     ═══════════════════════════════════════════════════════════════════════════ */
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: T.bg, overflow: 'hidden' }}>

      {/* ─────────────────────────── 1. HEADER ROW ─────────────────────────── */}
      <div style={{ padding: '12px 16px', borderBottom: `1px solid ${T.border}`, background: T.surface, flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10, flexWrap: 'wrap', gap: 10 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
              <span style={{ fontSize: 12, fontWeight: 700, color: T.text, ...mono, letterSpacing: '0.08em' }}>
                📡 NSE SMART SCANNER
              </span>
              <span style={{
                fontSize: 9, padding: '2px 7px', borderRadius: 3,
                background: T.accentDim, color: T.accent, ...mono,
                border: `1px solid ${T.accent}30`,
              }}>
                5-MIN SCAN
              </span>
              <span style={{
                fontSize: 9, padding: '2px 7px', borderRadius: 3,
                background: `${biasColor}10`, color: biasColor, ...mono,
                border: `1px solid ${biasColor}30`,
              }}>
                MARKET: {marketBias}
              </span>
            </div>
            {scanTime && (
              <div style={{ fontSize: 9, color: T.textDim, marginTop: 4, ...mono }}>
                Scanned {new Date(scanTime).toLocaleTimeString('en-IN', { hour12: true })} IST
                &nbsp;·&nbsp;
                {signals.length} stocks analysed
              </div>
            )}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            {nextScan && !loading && (
              <div style={{ fontSize: 9, color: T.textDim, display: 'flex', alignItems: 'center', gap: 5 }}>
                <span style={{ color: T.textDim, ...mono }}>NEXT:</span>
                <Countdown target={nextScan} onFire={runScan} />
              </div>
            )}
            <button onClick={runScan} disabled={loading} style={{
              padding: '6px 14px', borderRadius: 5,
              border: `1px solid ${T.accent}50`,
              background: loading ? T.border : T.accentDim,
              color: loading ? T.textDim : T.accent,
              fontSize: 10, fontWeight: 700,
              cursor: loading ? 'not-allowed' : 'pointer',
              ...mono, transition: 'all 0.2s',
            }}>
              {loading ? '⟳ SCANNING...' : '⟳ RESCAN'}
            </button>
          </div>
        </div>

        {/* Market-mood summary mini-cards */}
        <div style={{ display: 'flex', gap: 8 }}>
          {[
            { label: 'BUY SIGNALS',  count: buys,  color: T.green },
            { label: 'SELL SIGNALS', count: sells, color: T.red },
            { label: 'HOLD',         count: holds, color: T.gold },
          ].map(({ label, count, color }) => (
            <div key={label} style={{
              flex: 1, background: T.panel, borderRadius: 5, padding: '6px 10px',
              border: `1px solid ${T.border}`, textAlign: 'center',
            }}>
              <div style={{ fontSize: 16, fontWeight: 700, color, ...mono }}>{count}</div>
              <div style={{ fontSize: 8, color: T.textDim, letterSpacing: '0.08em' }}>{label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ─────────────────────── 2. CAPITAL INPUT BAR ──────────────────────── */}
      <div style={{
        padding: '10px 16px', borderBottom: `1px solid ${T.border}`,
        background: T.panelAlt, flexShrink: 0,
        display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
      }}>
        <span style={{ fontSize: 9, color: T.textDim, ...mono, letterSpacing: '0.08em', whiteSpace: 'nowrap' }}>
          💰 CAPITAL:
        </span>
        {PRESETS.map(p => (
          <button key={p.label} onClick={() => handlePreset(p.value)} style={{
            padding: '3px 9px', borderRadius: 4, fontSize: 9, fontWeight: 700,
            border: `1px solid ${capitalNum === p.value ? T.accent : T.border}`,
            background: capitalNum === p.value ? T.accentDim : 'transparent',
            color: capitalNum === p.value ? T.accent : T.textDim,
            cursor: 'pointer', ...mono, transition: 'all 0.15s',
          }}>
            {p.label}
          </button>
        ))}
        <div style={{
          display: 'flex', alignItems: 'center', background: T.bg,
          borderRadius: 5, overflow: 'hidden',
          border: `1px solid ${T.borderHi}`, flex: '1 1 120px', minWidth: 100, maxWidth: 220,
        }}>
          <span style={{ padding: '0 8px', fontSize: 13, color: T.textMid, ...mono }}>₹</span>
          <input
            value={capital}
            onChange={e => { setCapital(e.target.value); setAllocPlan(null); }}
            onKeyDown={e => e.key === 'Enter' && handleCapitalSubmit()}
            placeholder="Custom"
            style={{
              flex: 1, padding: '6px 4px', background: 'transparent',
              border: 'none', outline: 'none', color: T.text, fontSize: 12,
              ...mono, fontWeight: 700, width: 60,
            }}
          />
          {capitalNum > 0 && (
            <span style={{ padding: '0 8px', fontSize: 9, color: T.textDim, ...mono, whiteSpace: 'nowrap' }}>
              {fmtINR(capitalNum)}
            </span>
          )}
        </div>
        <button onClick={handleCapitalSubmit} disabled={capitalNum < 500 || allocLoading} style={{
          padding: '5px 12px', borderRadius: 5, border: 'none',
          background: (capitalNum < 500 || allocLoading) ? T.border : T.accent,
          color: '#fff', fontSize: 9, fontWeight: 700, cursor: (capitalNum < 500 || allocLoading) ? 'not-allowed' : 'pointer',
          ...mono, transition: 'all 0.2s', whiteSpace: 'nowrap',
          opacity: (capitalNum < 500 || allocLoading) ? 0.5 : 1,
        }}>
          {allocLoading ? '⟳ ALLOCATING...' : '📡 ALLOCATE'}
        </button>
      </div>

      {/* ────────────── 3. PROFIT SUMMARY BANNER (conditional) ─────────────── */}
      {showProfitBanner && (
        <div style={{
          margin: '10px 14px 0', padding: '14px 18px', borderRadius: 8,
          background: `linear-gradient(135deg, rgba(0,229,168,0.12), rgba(0,229,168,0.04))`,
          border: `1px solid rgba(0,229,168,0.35)`,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          flexWrap: 'wrap', gap: 12, flexShrink: 0,
        }}>
          <div>
            <div style={{ fontSize: 9, color: T.green, letterSpacing: '0.12em', ...mono, fontWeight: 700, marginBottom: 4 }}>
              🎯 TARGET PROFIT IF ALL SIGNALS HIT
            </div>
            <div style={{
              fontSize: 28, fontWeight: 900, color: T.green, ...mono,
              letterSpacing: '-0.03em', textShadow: `0 0 20px ${T.greenGlow}`,
            }}>
              +{fmtINR(allocPlan.total_potential_profit)}
            </div>
            <div style={{ fontSize: 11, color: T.green, opacity: 0.8, marginTop: 2 }}>
              {allocPlan.total_profit_pct}% return on ₹{Number(allocPlan.capital).toLocaleString('en-IN')} capital
            </div>
          </div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            {[
              { label: 'DEPLOYED',     value: `${allocPlan.deployment_pct}%`, color: T.blue },
              { label: 'MAX LOSS',     value: `-${fmtINR(allocPlan.total_potential_loss)}`, color: T.red },
              { label: 'PORTFOLIO R:R', value: `1:${allocPlan.portfolio_rr}`, color: allocPlan.portfolio_rr >= 2 ? T.green : T.gold },
            ].map(({ label, value, color }) => (
              <div key={label} style={{
                background: T.panel, borderRadius: 6, padding: '8px 12px',
                border: `1px solid ${T.border}`, textAlign: 'center', minWidth: 80,
              }}>
                <div style={{ fontSize: 7, color: T.textDim, letterSpacing: '0.1em', ...mono, marginBottom: 3 }}>{label}</div>
                <div style={{ fontSize: 13, fontWeight: 700, color, ...mono }}>{value}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ───────────────────────── 4. FILTER BAR ───────────────────────────── */}
      <FilterBar filter={filter} onFilter={setFilter} count={filtered.length} />

      {/* ─────────────────────────── 5. BODY ────────────────────────────────── */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 10 }}>

        {/* Loading spinner */}
        {loading && (
          <div style={{ textAlign: 'center', padding: '60px 0' }}>
            <div style={{
              display: 'inline-flex', alignItems: 'center', gap: 12,
              padding: '16px 24px', borderRadius: 8, background: T.panel,
              border: `1px solid ${T.border}`,
            }}>
              <span style={{
                display: 'inline-block', width: 16, height: 16,
                border: `2px solid ${T.border}`, borderTopColor: T.accent,
                borderRadius: '50%', animation: 'sp_spin 0.7s linear infinite',
              }} />
              <div>
                <div style={{ fontSize: 12, color: T.text, ...mono }}>SCANNING NSE STOCKS</div>
                <div style={{ fontSize: 10, color: T.textDim, marginTop: 3 }}>
                  Fetching 5-min data · Computing RSI, MACD, VWAP...
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Allocation scan progress (when loading allocation with capital) */}
        {allocLoading && !loading && (
          <ScanProgress elapsed={allocElapsed} />
        )}

        {/* Error / Offline banner */}
        {error && !loading && (
          <div style={{
            padding: '10px 14px', borderRadius: 6,
            background: 'rgba(245,200,66,0.06)',
            border: '1px solid rgba(245,200,66,0.15)',
            fontSize: 10, color: T.gold, ...mono, lineHeight: 1.4,
            display: 'flex', alignItems: 'center', gap: 8,
          }}>
            <span style={{
              display: 'inline-block', width: 6, height: 6, borderRadius: '50%',
              background: T.gold, animation: 'sp_pulse 1.5s infinite',
            }} />
            <span>⚠ BACKEND OFFLINE — {error}</span>
          </div>
        )}

        {/* Empty filter result */}
        {!loading && !error && filtered.length === 0 && signals.length > 0 && (
          <div style={{ textAlign: 'center', padding: '40px 0', color: T.textDim, fontSize: 12 }}>
            No {filter} signals at this time
          </div>
        )}

        {/* No signals at all (backend offline, no fallback) */}
        {!loading && signals.length === 0 && !error && (
          <div style={{ textAlign: 'center', padding: '60px 0', color: T.textDim, fontSize: 12, ...sans }}>
            No signals loaded yet. Click RESCAN to fetch.
          </div>
        )}

        {/* Signal cards */}
        {!loading && filtered.map(sig => (
          <SignalCard
            key={sig.symbol}
            sig={sig}
            onSelect={onSelectSymbol}
            isSelected={selectedSymbol === sig.symbol}
            livePriceData={prices?.[sig.symbol]}
            allocation={allocMap[sig.symbol] || null}
          />
        ))}

        {/* ──────────────────────── 6. DISCLAIMER ──────────────────────────── */}
        {!loading && signals.length > 0 && (
          <div style={{
            padding: '12px 14px', borderRadius: 6, background: T.panel,
            border: `1px solid ${T.border}`, marginTop: 4,
          }}>
            <div style={{ fontSize: 9, color: T.textDim, lineHeight: 1.6 }}>
              ⚖ <strong style={{ color: T.textMid }}>DISCLAIMER:</strong> These are algorithmic signals based
              on technical analysis of real market data. They are NOT financial advice. Past technical patterns
              do not guarantee future results. Always use proper position sizing, stop-losses, and your own
              judgement. Trade at your own risk. Square off all intraday positions before <strong style={{ color: T.textMid }}>3:20 PM IST</strong>.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
