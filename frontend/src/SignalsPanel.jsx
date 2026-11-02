import React, { useState, useEffect, useRef, useCallback } from 'react';
import { apiFetch } from './api';
import { T, mono, fmt, fmtINR, fmtPct } from './theme';

const SIGNAL_CFG = {
  'BUY':       { color: T.green, bg: T.greenDim, glow: T.greenGlow,  icon: '▲', label: 'BUY'       },
  'WEAK BUY':  { color: '#7bdb9e', bg: 'rgba(123,219,158,0.08)', glow: 'rgba(123,219,158,0.2)', icon: '△', label: 'WEAK BUY'  },
  'HOLD':      { color: '#f5c842',  bg: 'rgba(245,200,66,0.12)',  glow: 'rgba(245,200,66,0.2)',  icon: '◆', label: 'HOLD'      },
  'WEAK SELL': { color: '#ff9a7b', bg: 'rgba(255,154,123,0.08)', glow: 'rgba(255,154,123,0.2)', icon: '▽', label: 'WEAK SELL' },
  'SELL':      { color: T.red,   bg: T.redDim,   glow: T.redGlow,    icon: '▼', label: 'SELL'      },
};

const PRESETS = [
  { label: '₹500',  value: 500 },
  { label: '₹1K',   value: 1000 },
  { label: '₹5K',   value: 5000 },
  { label: '₹10K',  value: 10000 },
  { label: '₹25K',  value: 25000 },
  { label: '₹50K',  value: 50000 },
  { label: '₹1L',   value: 100000 },
];

const SCAN_STEPS = [
  "Fetching live NSE OHLCV data...",
  "Screening high-volatility universe...",
  "Evaluating candlestick bible rules...",
  "Applying 9/21 EMA trend check...",
  "Computing RSI & MACD momentum...",
  "Gating via daily macro trend...",
  "Filtering out ADX low trend items...",
  "Applying ATR risk stop metrics...",
  "Running position allocator...",
  "Wiring PDF mentor suggestions..."
];





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
  return <span style={{ ...mono, fontSize: 10, color: secs < 60 ? '#f5c842' : T.textDim }}>
    {String(m).padStart(2,'0')}:{String(s).padStart(2,'0')}
  </span>;
}

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

function ScanProgress({ elapsed }) {
  const step = Math.min(Math.floor(elapsed / 12), SCAN_STEPS.length - 1);
  const pct  = Math.min(97, (elapsed / 120) * 100);
  return (
    <div style={{ background: T.panel, border: `1px solid ${T.border}`,
      borderRadius: 12, padding: 18, display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        <div style={{ position: 'relative', width: 36, height: 36, flexShrink: 0 }}>
          <div style={{ position: 'absolute', inset: 0, borderRadius: '50%', border: `3px solid ${T.border}` }} />
          <div style={{ position: 'absolute', inset: 0, borderRadius: '50%', border: `3px solid transparent`, borderTopColor: T.accent, animation: 'spin 0.9s linear infinite' }} />
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14 }}></div>
        </div>
        <div>
          <div style={{ fontSize: 12, fontWeight: 700, color: T.text, fontFamily: "'IBM Plex Mono', monospace" }}>DEEP QUANTITATIVE SCANNING</div>
          <div style={{ fontSize: 10, color: T.textMid, marginTop: 3 }}>{elapsed}s — scanning high-volatility universe + sizing allocations</div>
        </div>
      </div>
      <div>
        <div style={{ height: 5, background: T.border, borderRadius: 4, overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${pct}%`, background: `linear-gradient(90deg, ${T.accent}, ${T.green})`, borderRadius: 4 }} />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 5, fontSize: 9, color: T.textDim, fontFamily: "'IBM Plex Mono', monospace" }}>
          <span>{SCAN_STEPS[step]}</span>
          <span>{Math.floor(pct)}%</span>
        </div>
      </div>
      {elapsed > 5 && (
        <div style={{
          fontSize: 10,
          color: '#ffd700',
          background: 'rgba(255, 215, 0, 0.08)',
          border: '1px solid rgba(255, 215, 0, 0.25)',
          borderRadius: 8,
          padding: '8px 12px',
          lineHeight: 1.4,
          fontFamily: "'IBM Plex Mono', monospace",
          animation: 'shimmer 2s infinite ease-in-out'
        }}>
           Cloud server cold-start detected. Waking up server threads on Hugging Face. This can take up to 45 seconds on the free tier. Please stand by...
        </div>
      )}
    </div>
  );
}

function ProfitBanner({ profit, profitPct, capital }) {
  const isGood = profit > 0;
  return (
    <div style={{
      background: isGood ? `linear-gradient(135deg, rgba(0,229,168,0.15), rgba(0,229,168,0.03))` : T.redDim,
      border: `1px solid ${isGood ? 'rgba(0,229,168,0.3)' : 'rgba(255,61,90,0.2)'}`,
      borderRadius: 12, padding: '16px 20px',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      flexWrap: 'wrap', gap: 12,
    }}>
      <div>
        <div style={{ fontSize: 9, color: isGood ? T.green : T.red, letterSpacing: '0.12em', fontFamily: "'IBM Plex Mono', monospace", marginBottom: 6, fontWeight: 700 }}>
           TARGET PORTFOLIO PROFIT IF TARGETS HIT
        </div>
        <div style={{ fontSize: 30, fontWeight: 900, color: isGood ? T.green : T.red, fontFamily: "'IBM Plex Mono', monospace", textShadow: isGood ? `0 0 20px ${T.greenGlow}` : 'none' }}>
          +{fmtINR(profit)}
        </div>
        <div style={{ fontSize: 11, color: isGood ? T.green : T.red, marginTop: 4, opacity: 0.8 }}>
          {profitPct}% profit target on ₹{Number(capital).toLocaleString('en-IN')} trading capital
        </div>
      </div>
      <div style={{ textAlign: 'right' }}>
        <div style={{ fontSize: 9, color: T.textMid, fontFamily: "'IBM Plex Mono', monospace", marginBottom: 4 }}>RETURN TIER</div>
        <div style={{ fontSize: 15, fontWeight: 700, fontFamily: "'IBM Plex Mono', monospace", color: profitPct >= 15 ? '#f5c842' : profitPct >= 8 ? T.green : T.textMid }}>
          {profitPct >= 20 ? ' AGGRESSIVE' : profitPct >= 12 ? ' HIGH RETURN' : profitPct >= 7 ? ' GOOD RETURN' : ' MODERATE'}
        </div>
      </div>
    </div>
  );
}

function SignalCard({ sig, onSelect, isSelected, livePriceData, allocation }) {
  const [openMentor, setOpenMentor] = useState(false);
  const cfg = SIGNAL_CFG[sig.signal] || SIGNAL_CFG['HOLD'];
  const isBull = sig.signal.includes('BUY');
  const isBear = sig.signal.includes('SELL');

  const currentPrice = livePriceData?.price ?? sig.price;
  const isBullTrade = sig.signal.includes('BUY');
  const isBearTrade = sig.signal.includes('SELL');

  let liveReturnPct = 0;
  if (currentPrice && sig.entry && (isBullTrade || isBearTrade)) {
    liveReturnPct = isBullTrade
      ? ((currentPrice - sig.entry) / sig.entry) * 100
      : ((sig.entry - currentPrice) / sig.entry) * 100;
  }

  const pnlColor = liveReturnPct > 0 ? T.green : liveReturnPct < 0 ? T.red : T.textMid;
  const pnlValue = (isBullTrade || isBearTrade) ? `${liveReturnPct > 0 ? '+' : ''}${liveReturnPct.toFixed(2)}%` : '—';

  return (
    <div
      onClick={() => onSelect(sig.symbol)}
      style={{
        background: isSelected ? `${cfg.color}08` : T.panel,
        border: `1px solid ${isSelected ? cfg.color + '50' : T.border}`,
        borderLeft: `3px solid ${cfg.color}`,
        borderRadius: 10,
        padding: '14px 16px',
        cursor: 'pointer',
        transition: 'all 0.2s',
        boxShadow: isSelected ? `0 0 20px ${cfg.glow}` : 'none',
        animation: 'fadeIn 0.3s ease',
      }}
      onMouseEnter={e => !isSelected && (e.currentTarget.style.borderColor = cfg.color + '40')}
      onMouseLeave={e => !isSelected && (e.currentTarget.style.borderColor = T.border)}
    >
      {/* Symbol, Sector & Signal Badge */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 13, fontWeight: 700, color: T.text, ...mono, letterSpacing: '0.03em' }}>
              {sig.symbol.replace('.NS', '')}
            </span>
            <span style={{ fontSize: 9, color: T.textDim, background: T.surface, padding: '2px 6px', borderRadius: 3, border: `1px solid ${T.border}` }}>
              {sig.sector}
            </span>
            {sig.top_pattern && (
              <span style={{ fontSize: 9, color: '#f5c842', background: 'rgba(245,200,66,0.12)', padding: '2px 6px', borderRadius: 3, border: `1px solid ${'#f5c842'}40`, ...mono, fontWeight: 700 }}>
                 {sig.top_pattern}
              </span>
            )}
          </div>
          <div style={{ fontSize: 10, color: T.textDim, marginTop: 2 }}>{sig.name}</div>
        </div>
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 5,
          padding: '4px 10px', borderRadius: 5,
          background: cfg.bg, border: `1px solid ${cfg.color}30`,
          fontSize: 10, fontWeight: 700, color: cfg.color, ...mono,
          boxShadow: `0 0 10px ${cfg.glow}`,
        }}>
          <span>{cfg.icon}</span>
          <span>{cfg.label}</span>
        </div>
      </div>

      {/* Target and Stop ratios */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 6, marginBottom: 8 }}>
        {[
          { label: 'ENTRY', value: `₹${fmt(sig.entry)}`, color: T.text },
          { label: 'CURRENT', value: `₹${fmt(currentPrice)}`, color: T.blue, isLive: true },
          { label: 'TARGET', value: `₹${fmt(sig.target)}`, color: isBull ? T.green : isBear ? T.red : '#f5c842' },
          { label: 'STOP', value: `₹${fmt(sig.stop_loss)}`, color: isBull ? T.red : isBear ? T.green : T.textMid },
          { label: 'LIVE P&L', value: pnlValue, color: pnlColor },
        ].map(({ label, value, color, isLive }) => (
          <div key={label} style={{ background: T.surface, padding: '6px 8px', borderRadius: 5, border: `1px solid ${T.border}`, position: 'relative' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
              <div style={{ fontSize: 8, color: T.textDim, letterSpacing: '0.08em', ...mono }}>{label}</div>
              {isLive && livePriceData && (
                <span style={{ display: 'inline-block', width: 4, height: 4, borderRadius: '50%', background: T.green, animation: 'pulse 1.2s infinite' }} />
              )}
            </div>
            <div style={{ fontSize: 11, color, fontWeight: 700, ...mono }}>{value}</div>
          </div>
        ))}
      </div>

      {/* Stats row */}
      <div style={{ marginBottom: 8 }}>
        <span style={{ fontSize: 9, color: isBull ? T.green : isBear ? T.red : '#f5c842', ...mono }}>
          {fmtPct(sig.target_pct)} target move
        </span>
        <span style={{ fontSize: 9, color: T.textDim, marginLeft: 8 }}>
          ATR: ₹{fmt(sig.atr)}
        </span>
        <span style={{ fontSize: 9, color: T.textDim, marginLeft: 8 }}>
          R:R: 1:{sig.rr_ratio}
        </span>
      </div>

      {/* Indicators */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5, marginBottom: 8 }}>
        <Badge label="RSI" value={sig.rsi} color={sig.rsi > 70 ? T.red : sig.rsi < 30 ? T.green : sig.rsi > 55 ? '#7bdb9e' : T.textMid} />
        <Badge label="VWAP" value={currentPrice > sig.vwap ? '↑ Above' : '↓ Below'} color={currentPrice > sig.vwap ? T.green : T.red} />
        <Badge label="EMA" value={sig.ema9 > sig.ema21 ? '9>21 Bull' : '9<21 Bear'} color={sig.ema9 > sig.ema21 ? T.green : T.red} />
        <Badge label="VOL" value={`${sig.vol_ratio}x`} color={sig.vol_ratio >= 1.5 ? T.blue : sig.vol_ratio < 0.7 ? T.textDim : T.textMid} />
        <Badge label="MACD" value={sig.macd_hist > 0 ? '▲ Bull' : '▼ Bear'} color={sig.macd_hist > 0 ? T.green : T.red} />
      </div>

      {/* Technical reasons */}
      {sig.reasoning && (
        <div style={{ fontSize: 10, color: T.textMid, lineHeight: 1.5, padding: '8px 10px', background: T.surface, borderRadius: 5, border: `1px solid ${T.border}`, borderLeft: `2px solid ${cfg.color}40`, marginBottom: 8 }}>
          {sig.reasoning}
        </div>
      )}

      {/* CAPITAL ALLOCATION SECTION (Merged view) */}
      {allocation ? (
        <div style={{ background: 'rgba(0, 229, 168, 0.02)', border: `1px solid rgba(0, 229, 168, 0.25)`, borderRadius: 8, padding: 12, marginTop: 10, cursor: 'default' }} onClick={e => e.stopPropagation()}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <span style={{ fontSize: 9, fontWeight: 700, color: T.green, fontFamily: "'IBM Plex Mono', monospace", letterSpacing: '0.08em' }}> CAPITAL ALLOCATION APPROVED</span>
            <span style={{ fontSize: 9, color: T.textMid, ...mono }}>{allocation.allocation_pct}% of capital</span>
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 6 }}>
            {[
              { label: "SHARES TO BUY", val: `${allocation.shares} shares`, color: T.text },
              { label: "TOTAL COST", val: fmtINR(allocation.amount_invested), color: T.blue },
              { label: "TARGET PROFIT", val: `+${fmtINR(allocation.potential_profit)}`, color: T.green },
              { label: "MAX LOSS LIMIT", val: `-${fmtINR(allocation.potential_loss)}`, color: T.red }
            ].map(col => (
              <div key={col.label} style={{ background: T.surface, border: `1px solid ${T.border}`, padding: '6px 8px', borderRadius: 4 }}>
                <div style={{ fontSize: 7, color: T.textDim, fontFamily: "'IBM Plex Mono', monospace" }}>{col.label}</div>
                <div style={{ fontSize: 11, fontWeight: 700, color: col.color, marginTop: 2, ...mono }}>{col.val}</div>
              </div>
            ))}
          </div>

          {/* AI Mentor Advice from PDFs */}
          {allocation.mentor_advice && (
            <div style={{ marginTop: 8 }}>
              <div 
                onClick={() => setOpenMentor(!openMentor)}
                style={{ fontSize: 9, color: T.accent, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, fontFamily: "'IBM Plex Mono', monospace", padding: '4px 0' }}
              >
                <span>{openMentor ? '▼' : '▶'}</span>
                <span>✦ AI MENTOR WISDOM (FROM PDFs)</span>
              </div>
              {openMentor && (
                <div style={{ background: T.bg, padding: '8px 10px', borderRadius: 6, border: `1px solid ${T.border}`, display: 'flex', flexDirection: 'column', gap: 5, marginTop: 4 }}>
                  {allocation.mentor_advice.map((adv, ai) => (
                    <div key={ai} style={{ fontSize: 9.5, color: adv.includes("Risk") ? T.red : adv.includes("Bible") ? T.green : T.textMid, lineHeight: 1.4 }}>
                      {adv}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      ) : (
        isBull && (
          <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 8, padding: '8px 12px', marginTop: 10, fontSize: 10, color: T.textDim, textAlign: 'center' }}>
            No capital allocated to this position (budget limit reached or lower conviction score)
          </div>
        )
      )}

      {!allocation && !isBull && (
        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 8, padding: '8px 12px', marginTop: 10, fontSize: 10, color: T.textDim, textAlign: 'center' }}>
          {isBear ? 'Short position skipped (long-only capital allocation)' : 'Neutral hold signal — cash preserved in reserve'}
        </div>
      )}

      <div style={{ marginTop: 8 }}>
        <ConfBar confidence={sig.confidence} signal={sig.signal} />
      </div>
    </div>
  );
}

function FilterBar({ filter, onFilter, count, sectorFilter, onSectorFilter, minConf, onMinConf, minRR, onMinRR, availableSectors }) {
  const filters = ['ALL', 'BUY', 'WEAK BUY', 'HOLD', 'WEAK SELL', 'SELL'];
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, padding: '10px 16px', borderBottom: `1px solid ${T.border}` }}>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
        {filters.map(f => {
          const cfg = f === 'ALL' ? { color: T.accent, bg: T.accentDim } : (SIGNAL_CFG[f] || { color: T.textMid, bg: 'transparent' });
          const active = filter === f;
          return (
            <button key={f} className="smooth-button" onClick={() => onFilter(f)} style={{
              padding: '4px 10px', borderRadius: 4, border: `1px solid ${active ? cfg.color + '60' : T.border}`,
              background: active ? cfg.bg : 'transparent', color: active ? cfg.color : T.textDim,
              fontSize: 9, fontWeight: 700, cursor: 'pointer', ...mono, letterSpacing: '0.06em',
              transition: 'all 0.15s',
            }}>
              {f === 'ALL' ? `ALL (${count})` : f}
            </button>
          );
        })}
      </div>
      
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 9, color: T.textMid, ...mono }}>SECTOR:</span>
          <select value={sectorFilter} onChange={e => onSectorFilter(e.target.value)} style={{ padding: '2px 6px', fontSize: 10, ...mono, background: T.bg, color: T.text, border: `1px solid ${T.borderHi}`, borderRadius: 4 }}>
            <option value="ALL">ALL SECTORS</option>
            {availableSectors.map(sec => <option key={sec} value={sec}>{sec.toUpperCase()}</option>)}
          </select>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 9, color: T.textMid, ...mono }}>MIN CONF:</span>
          <select value={minConf} onChange={e => onMinConf(parseInt(e.target.value))} style={{ padding: '2px 6px', fontSize: 10, ...mono, background: T.bg, color: T.text, border: `1px solid ${T.borderHi}`, borderRadius: 4 }}>
            <option value={0}>ANY %</option>
            <option value={60}>&gt; 60%</option>
            <option value={75}>&gt; 75%</option>
            <option value={85}>&gt; 85%</option>
            <option value={95}>&gt; 95%</option>
          </select>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 9, color: T.textMid, ...mono }}>MIN R:R:</span>
          <select value={minRR} onChange={e => onMinRR(parseFloat(e.target.value))} style={{ padding: '2px 6px', fontSize: 10, ...mono, background: T.bg, color: T.text, border: `1px solid ${T.borderHi}`, borderRadius: 4 }}>
            <option value={0}>ANY R:R</option>
            <option value={1.5}>&gt; 1:1.5</option>
            <option value={2.0}>&gt; 1:2.0</option>
            <option value={3.0}>&gt; 1:3.0</option>
          </select>
        </div>
      </div>
    </div>
  );
}

export default function SignalsPanel({ onSelectSymbol, selectedSymbol, prices, cash }) {
  const [capital, setCapital]   = useState(cash ? String(cash) : '10000');
  const [selectedStyle, setSelectedStyle] = useState('Intraday Momentum');
  const [plan, setPlan]         = useState(null);
  const [loading, setLoading]   = useState(false);
  const [elapsed, setElapsed]   = useState(0);
  const [error, setError]       = useState(null);
  const [filter, setFilter]     = useState('ALL');
  const [sectorFilter, setSectorFilter] = useState('ALL');
  const [minConf, setMinConf]   = useState(0);
  const [minRR, setMinRR]       = useState(0);
  const [nextScan, setNextScan] = useState(null);
  const timerRef = useRef(null);
  const abortRef = useRef(null);

  const REFRESH_MS = 5 * 60 * 1000;

  useEffect(() => {
    if (loading) {
      setElapsed(0);
      timerRef.current = setInterval(() => setElapsed(e => e + 1), 1000);
    } else {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [loading]);

  const runScanAndAllocate = useCallback(async () => {
    const amt = parseFloat(capital.replace(/,/g, ''));
    if (!amt || amt < 500) {
      setError('Minimum trading capital required is ₹500');
      return;
    }

    if (abortRef.current) abortRef.current.abort();
    abortRef.current = new AbortController();

    setLoading(true);
    setError(null);

    // Yield to the browser event loop to paint loading UI immediately (fixes INP issues)
    await new Promise(resolve => setTimeout(resolve, 0));

    try {
      const res = await apiFetch('/api/allocate', {
        method: 'POST',
        body: JSON.stringify({ 
          capital: amt,
          trading_style: selectedStyle
        }),
        signal: abortRef.current.signal,
      });
      if (res.status === 401) {
        localStorage.removeItem('is_logged_in');
        localStorage.removeItem('apex_user');
        localStorage.removeItem('apt_token');
        sessionStorage.removeItem('apt_token');
        window.location.reload();
        return;
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      
      if (data.all_signals && data.all_signals.length > 0) {
        setPlan(data);
      } else {
        setPlan({ all_signals: [], allocations: [] });
        setError("Backend signal engine returning empty. No active market signals.");
      }
      setNextScan(Date.now() + REFRESH_MS);
    } catch (e) {
      if (e.name !== 'AbortError') {
        setPlan({ all_signals: [], allocations: [] });
        setError("Backend unavailable or scan failed. No signals to display.");
        setNextScan(Date.now() + REFRESH_MS);
      }
    } finally {
      setLoading(false);
    }
  }, [capital, selectedStyle]);

  // Initial scan on mount
  useEffect(() => {
    runScanAndAllocate();
  }, []);

  const displayAmt = parseFloat(capital.replace(/,/g, '')) || 0;
  const signals = plan?.all_signals || [];
  
  const availableSectors = [...new Set(signals.map(s => s.sector || 'Unknown'))].sort();
  
  const filtered = signals.filter(s => {
    if (filter !== 'ALL' && s.signal !== filter) return false;
    if (sectorFilter !== 'ALL' && (s.sector || 'Unknown') !== sectorFilter) return false;
    if (s.confidence < minConf) return false;
    
    const rr = (s.target && s.stop_loss && s.current_price && Math.abs(s.current_price - s.stop_loss) > 0) 
      ? Math.abs((s.target - s.current_price) / (s.current_price - s.stop_loss)) 
      : 0;
      
    if (rr < minRR) return false;
    return true;
  });

  const buys  = signals.filter(s => s.signal === 'BUY' || s.signal === 'WEAK BUY').length;
  const sells = signals.filter(s => s.signal === 'SELL' || s.signal === 'WEAK SELL').length;
  const holds = signals.filter(s => s.signal === 'HOLD').length;
  const marketBias = buys > sells + 1 ? 'BULLISH' : sells > buys + 1 ? 'BEARISH' : 'NEUTRAL';
  const biasColor  = marketBias === 'BULLISH' ? T.green : marketBias === 'BEARISH' ? T.red : '#f5c842';

  // Map allocations by symbol for O(1) lookup
  const allocationsMap = {};
  if (plan?.positions) {
    plan.positions.forEach(pos => {
      allocationsMap[pos.symbol] = pos;
    });
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: T.bg, overflowY: 'auto' }}>
      
      {/* Control panel: Capital sizing & triggers */}
      <div style={{ padding: '14px 16px', borderBottom: `1px solid ${T.border}`, background: T.surface, flexShrink: 0 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.12em', color: T.textMid, fontFamily: "'IBM Plex Mono', monospace" }}>
             QUANT SCANNER & CAPITAL ALLOCATOR
          </span>
          {nextScan && !loading && (
            <div style={{ fontSize: 9, color: T.textDim, display: 'flex', alignItems: 'center', gap: 5 }}>
              <span style={{ color: T.textDim, ...mono }}>AUTO-RESCAN:</span>
              <Countdown target={nextScan} onFire={runScanAndAllocate} />
            </div>
          )}
        </div>

        {/* Presets */}
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 12 }}>
          {PRESETS.map(p => (
            <button key={p.label}
              className="smooth-button"
              onClick={() => { setCapital(p.value.toString()); }}
              style={{
                padding: '4px 10px', borderRadius: 5, border: `1px solid ${displayAmt === p.value ? T.accent : T.border}`,
                background: displayAmt === p.value ? T.accentDim : T.bg,
                color: displayAmt === p.value ? T.accent : T.textMid,
                fontSize: 10, fontWeight: 700, cursor: 'pointer',
                fontFamily: "'IBM Plex Mono', monospace", transition: 'all 0.15s',
              }}>{p.label}</button>
          ))}
        </div>

        {/* Capital Input and Rescan Button */}
        <div style={{ display: 'flex', gap: 10 }}>
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', background: T.bg, borderRadius: 8, overflow: 'hidden', border: `1px solid ${T.borderHi}` }}>
            <span style={{ padding: '0 12px', fontSize: 16, color: T.textDim, fontFamily: "'IBM Plex Mono', monospace" }}>₹</span>
            <input
              value={capital} disabled={loading}
              onChange={e => setCapital(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && runScanAndAllocate()}
              placeholder="Enter capital size (e.g. ₹5,000)..."
              style={{ flex: 1, padding: '10px 4px', background: 'transparent', border: 'none', outline: 'none', color: T.text, fontSize: 13, fontFamily: "'IBM Plex Mono', monospace", fontWeight: 700 }}
            />
            {displayAmt > 0 && (
              <span style={{ padding: '0 12px', fontSize: 10, color: T.textDim, fontFamily: "'IBM Plex Mono', monospace", whiteSpace: 'nowrap' }}>
                {fmtINR(displayAmt)}
              </span>
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', background: T.bg, borderRadius: 8, overflow: 'hidden', border: `1px solid ${T.borderHi}`, padding: '0 8px' }}>
            <select
              value={selectedStyle}
              onChange={e => setSelectedStyle(e.target.value)}
              disabled={loading}
              style={{
                background: 'transparent',
                border: 'none',
                outline: 'none',
                color: T.text,
                fontSize: 11,
                fontFamily: "'IBM Plex Mono', monospace",
                fontWeight: 700,
                cursor: 'pointer',
                padding: '10px 4px',
              }}
            >
              <option value="Intraday Momentum" style={{ background: T.surface, color: T.text }}>DEFAULT SCANNER</option>
              <option value="My Strategy" style={{ background: T.surface, color: T.text }}>MY STRATEGY (PDFs)</option>
            </select>
          </div>

          <button onClick={runScanAndAllocate} disabled={loading} className="smooth-button" style={{
            padding: '10px 18px', borderRadius: 8, border: 'none',
            background: loading ? T.accentDim : T.accent, color: '#fff',
            fontWeight: 700, fontSize: 11, letterSpacing: '0.08em', cursor: 'pointer',
            fontFamily: "'IBM Plex Mono', monospace", whiteSpace: 'nowrap',
            display: 'flex', alignItems: 'center', gap: 8,
          }}>
            {loading ? '⟳ SCANNING...' : ' SCAN & SIZE'}
          </button>
        </div>
      </div>

      {/* Progress or results */}
      <div style={{ flex: 1, padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        {loading && <ScanProgress elapsed={elapsed} />}

        {error && !loading && (
          <div style={{
            padding: '9px 12px', borderRadius: 7, background: 'rgba(245,200,66,0.06)',
            border: `1px solid rgba(245,200,66,0.18)`, fontSize: 10, color: '#f5c842',
            fontFamily: "'IBM Plex Mono', monospace", lineHeight: 1.4, display: 'flex',
            alignItems: 'center', gap: 8
          }}>
            <span style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', background: '#f5c842', animation: 'pulse 1.5s infinite' }} />
            <span>{error}</span>
          </div>
        )}

        {!plan && !loading && !error && (
          <div style={{
            background: T.panel,
            border: `1px solid ${T.border}`,
            borderRadius: 12,
            padding: '36px 24px',
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 16,
            maxWidth: 580,
            margin: '32px auto',
            boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
          }}>
            <div style={{
              width: 56,
              height: 56,
              borderRadius: '50%',
              background: 'rgba(77, 166, 255, 0.08)',
              border: `1px solid rgba(77, 166, 255, 0.2)`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 22,
              animation: 'pulse 2s infinite'
            }}>
              
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <h3 style={{ fontSize: 14, fontWeight: 700, color: T.text, fontFamily: "'IBM Plex Mono', monospace", letterSpacing: '0.05em' }}>
                QUANT SCANNER READY
              </h3>
              <p style={{ fontSize: 10.5, color: T.textMid, lineHeight: 1.6, maxWidth: 420, margin: '0 auto' }}>
                Analyze the market universe in real-time. Enter your available trading capital above to calculate optimized position sizes and risk parameters.
              </p>
            </div>

            <div style={{
              width: '100%',
              maxWidth: 420,
              background: T.surface,
              border: `1px solid ${T.border}`,
              borderRadius: 8,
              padding: '12px 16px',
              textAlign: 'left',
              display: 'flex',
              flexDirection: 'column',
              gap: 8
            }}>
              <div style={{ fontSize: 8.5, color: T.textDim, fontWeight: 700, fontFamily: "'IBM Plex Mono', monospace", letterSpacing: '0.08em' }}>
                CORE SCANNING ENGINES
              </div>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                <span style={{ color: T.green, fontSize: 10 }}>✓</span>
                <span style={{ fontSize: 10, color: T.textMid }}>
                  <strong>Technical Indicators:</strong> Real-time checks for EMA crossovers, ADX choppiness gating, and RSI extremes.
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                <span style={{ color: T.green, fontSize: 10 }}>✓</span>
                <span style={{ fontSize: 10, color: T.textMid }}>
                  <strong>Price Action (PDF SMC):</strong> Verification of Engulfing patterns, Hammers, structural Break of Structure (BOS), and Change of Character (CHoCH).
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                <span style={{ color: T.green, fontSize: 10 }}>✓</span>
                <span style={{ fontSize: 10, color: T.textMid }}>
                  <strong>Risk Control:</strong> Dynamic ATR-based Stop Loss buffers and custom 1-2% capital exposure limits.
                </span>
              </div>
            </div>

            <button
              onClick={runScanAndAllocate}
              className="smooth-button"
              style={{
                padding: '10px 24px',
                borderRadius: 8,
                border: 'none',
                background: T.accent,
                color: '#fff',
                fontWeight: 700,
                fontSize: 11,
                letterSpacing: '0.08em',
                cursor: 'pointer',
                fontFamily: "'IBM Plex Mono', monospace",
                boxShadow: `0 4px 14px ${T.accent}40`,
                transition: 'all 0.2s'
              }}
            >
              RUN MARKET SCAN
            </button>
            
            <p style={{ fontSize: 8.5, color: T.textDim, fontFamily: "'IBM Plex Mono', monospace" }}>
              *Scans analyze high-volatility NSE listings and run in 5-15 seconds.
            </p>
          </div>
        )}

        {plan && !loading && (
          <>
            {/* Portfolio target allocation profit header */}
            {plan.positions && plan.positions.length > 0 && (
              <ProfitBanner
                profit={plan.total_potential_profit}
                profitPct={plan.total_profit_pct}
                capital={plan.capital}
              />
            )}

            {/* Summary statistics row */}
            {plan.positions && plan.positions.length > 0 && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
                {[
                  { label: 'CAPITAL',   val: fmtINR(plan.capital),           color: T.text },
                  { label: 'DEPLOYED',  val: fmtINR(plan.total_deployed),    color: T.blue, sub: `${plan.deployment_pct}%` },
                  { label: 'MAX RISK',  val: `-${fmtINR(plan.total_potential_loss)}`, color: T.red, sub: `${plan.max_risk_pct}% limit` },
                  { label: 'PORTFOLIO RR', val: `1 : ${plan.portfolio_rr}`, color: plan.portfolio_rr >= 2 ? T.green : '#f5c842' },
                ].map(({ label, val, color, sub }) => (
                  <div key={label} style={{ background: T.panel, border: `1px solid ${T.border}`, borderRadius: 8, padding: '10px 12px' }}>
                    <div style={{ fontSize: 7, color: T.textDim, letterSpacing: '0.08em', fontFamily: "'IBM Plex Mono', monospace" }}>{label}</div>
                    <div style={{ fontSize: 13, fontWeight: 700, color, marginTop: 3, ...mono }}>{val}</div>
                    {sub && <div style={{ fontSize: 8, color: T.textDim, marginTop: 2 }}>{sub}</div>}
                  </div>
                ))}
              </div>
            )}

            {/* Watchlist statistics */}
            <div style={{ display: 'flex', gap: 6, background: T.surface, border: `1px solid ${T.border}`, borderRadius: 8, padding: 6, justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', gap: 10, marginLeft: 8 }}>
                <span style={{ fontSize: 9, ...mono, color: T.textMid }}>MARKET MOOD: <strong style={{ color: biasColor }}>{marketBias}</strong></span>
                <span style={{ fontSize: 9, ...mono, color: T.textDim }}>|</span>
                <span style={{ fontSize: 9, ...mono, color: T.textMid }}>BUYS: <strong style={{ color: T.green }}>{buys}</strong></span>
                <span style={{ fontSize: 9, ...mono, color: T.textMid }}>SELLS: <strong style={{ color: T.red }}>{sells}</strong></span>
              </div>
              <span style={{ fontSize: 9, ...mono, color: T.textDim, marginRight: 8 }}>
                {signals.length} STOCKS SCANNED
              </span>
            </div>

            {/* Filter Bar */}
            <FilterBar 
              filter={filter} onFilter={setFilter} count={filtered.length} 
              sectorFilter={sectorFilter} onSectorFilter={setSectorFilter}
              minConf={minConf} onMinConf={setMinConf}
              minRR={minRR} onMinRR={setMinRR}
              availableSectors={availableSectors}
            />

            {/* List of cards */}
            {filtered.length === 0 ? (
              <div style={{ padding: '32px', textAlign: 'center', background: T.panel, border: `1px solid ${T.border}`, borderRadius: 12, color: T.textDim, fontSize: 11 }}>
                No {filter} signals scanned on current watchlist
              </div>
            ) : (
              filtered.map(sig => (
                <SignalCard
                  key={sig.symbol}
                  sig={sig}
                  onSelect={onSelectSymbol}
                  isSelected={selectedSymbol === sig.symbol}
                  livePriceData={prices?.[sig.symbol]}
                  allocation={allocationsMap[sig.symbol]}
                />
              ))
            )}

            {/* Disclaimer and PDF compliance notes */}
            <div style={{ padding: '12px 14px', borderRadius: 8, background: T.panel, border: `1px solid ${T.border}`, display: 'flex', flexDirection: 'column', gap: 6 }}>
              <div style={{ fontSize: 8.5, color: T.textDim, lineHeight: 1.5 }}>
                ✦ <strong>PDF GUIDE COMPLIANCE:</strong> All trades are size-gated based on the 1-2% maximum capital risk rule from the SL Guide. Stop losses are calculated using ATR multipliers to prevent market-maker stop-runs. Candlestick patterns are verified against the Candlestick Bible.
              </div>
              <div style={{ fontSize: 8.5, color: T.textDim, lineHeight: 1.5, borderTop: `1px solid ${T.border}`, paddingTop: 6 }}>
                ⚠ Algorithmic tools only — not SEBI registered advice. Always paper-trade to verify strategies before allocating real funds. Trade responsibly.
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
