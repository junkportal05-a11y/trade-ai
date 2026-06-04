/**
 * CapitalAllocator.jsx  v3
 * High-return focus: shows ₹ profit prominently, targets 10-20% gains
 */

import { useState, useEffect, useCallback, useRef } from "react";

const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const T = {
  bg:        '#080a0f',
  surface:   '#0d1018',
  panel:     '#111520',
  card:      '#13182a',
  border:    '#1a1f2e',
  borderHi:  '#252c40',
  text:      '#d0d8ed',
  textMid:   '#6e7a96',
  textDim:   '#363d55',
  green:     '#00e5a8',
  greenDim:  'rgba(0,229,168,0.11)',
  greenGlow: 'rgba(0,229,168,0.25)',
  red:       '#ff3d5a',
  redDim:    'rgba(255,61,90,0.1)',
  gold:      '#f5c842',
  goldDim:   'rgba(245,200,66,0.1)',
  accent:    '#7b6cff',
  accentDim: 'rgba(123,108,255,0.12)',
  blue:      '#4da6ff',
  blueDim:   'rgba(77,166,255,0.08)',
};

const fmtINR = (n) => {
  if (n == null || isNaN(n)) return '—';
  if (n >= 1e7) return `₹${(n/1e7).toFixed(2)}Cr`;
  if (n >= 1e5) return `₹${(n/1e5).toFixed(2)}L`;
  if (n >= 1e3) return `₹${(n/1e3).toFixed(1)}K`;
  return `₹${Number(n).toFixed(0)}`;
};
const fmt2 = (n) => Number(n).toFixed(2);

const PRESETS = [
  { label:'₹500',  value:500    },
  { label:'₹1K',   value:1000   },
  { label:'₹2K',   value:2000   },
  { label:'₹5K',   value:5000   },
  { label:'₹10K',  value:10000  },
  { label:'₹25K',  value:25000  },
  { label:'₹50K',  value:50000  },
  { label:'₹1L',   value:100000 },
];

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

function ScanProgress({ elapsed }) {
  const step = Math.min(Math.floor(elapsed / 10), SCAN_STEPS.length - 1);
  const pct  = Math.min(97, (elapsed / 110) * 100);
  return (
    <div style={{ background: T.panel, border: `1px solid ${T.border}`,
      borderRadius: 12, padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        <div style={{ position: 'relative', width: 42, height: 42, flexShrink: 0 }}>
          <div style={{ position: 'absolute', inset: 0, borderRadius: '50%',
            border: `3px solid ${T.border}` }} />
          <div style={{ position: 'absolute', inset: 0, borderRadius: '50%',
            border: `3px solid transparent`, borderTopColor: T.accent,
            animation: 'spin 0.9s linear infinite' }} />
          <div style={{ position: 'absolute', inset: 0, display: 'flex',
            alignItems: 'center', justifyContent: 'center', fontSize: 16 }}>🔍</div>
        </div>
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, color: T.text,
            fontFamily: "'IBM Plex Mono', monospace" }}>DEEP MARKET ANALYSIS</div>
          <div style={{ fontSize: 10, color: T.textMid, marginTop: 3 }}>
            {elapsed}s — scanning high-volatility NSE stocks for best entries
          </div>
        </div>
      </div>

      <div>
        <div style={{ height: 7, background: T.border, borderRadius: 4, overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${pct}%`,
            background: `linear-gradient(90deg, ${T.accent}, ${T.green})`,
            borderRadius: 4, transition: 'width 1.2s ease' }} />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 5,
          fontSize: 9, color: T.textDim, fontFamily: "'IBM Plex Mono', monospace" }}>
          <span>{SCAN_STEPS[step]}</span>
          <span>{Math.floor(pct)}%</span>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
        {['RSI (14)', 'MACD (12/26/9)', 'EMA 9/21/50', 'Bollinger Bands',
          'VWAP', 'Supertrend', 'Volume Surge', 'ATR Sizing'].map((ind, i) => {
          const done = elapsed >= (i + 1) * 11;
          return (
            <div key={ind} style={{ display: 'flex', gap: 7, alignItems: 'center',
              fontSize: 10, fontFamily: "'IBM Plex Mono', monospace",
              color: done ? T.green : T.textDim, transition: 'color 0.5s' }}>
              <span style={{ fontSize: 11 }}>{done ? '✓' : '·'}</span>
              {ind}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ProfitBanner({ profit, profitPct, capital }) {
  const isGood = profit > 0;
  return (
    <div style={{
      background: isGood
        ? `linear-gradient(135deg, rgba(0,229,168,0.15), rgba(0,229,168,0.05))`
        : T.redDim,
      border: `1px solid ${isGood ? 'rgba(0,229,168,0.4)' : 'rgba(255,61,90,0.3)'}`,
      borderRadius: 12, padding: '20px 24px',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      flexWrap: 'wrap', gap: 16,
    }}>
      <div>
        <div style={{ fontSize: 10, color: isGood ? T.green : T.red, letterSpacing: '0.12em',
          fontFamily: "'IBM Plex Mono', monospace", marginBottom: 6, fontWeight: 700 }}>
          🎯 TARGET PROFIT IF ALL SIGNALS HIT
        </div>
        <div style={{ fontSize: 36, fontWeight: 900, color: isGood ? T.green : T.red,
          fontFamily: "'IBM Plex Mono', monospace", letterSpacing: '-0.03em',
          textShadow: isGood ? `0 0 30px ${T.greenGlow}` : 'none' }}>
          +{fmtINR(profit)}
        </div>
        <div style={{ fontSize: 13, color: isGood ? T.green : T.red, marginTop: 4,
          opacity: 0.8 }}>
          {profitPct}% return on ₹{Number(capital).toLocaleString('en-IN')} capital
        </div>
      </div>
      <div style={{ textAlign: 'right' }}>
        <div style={{ fontSize: 10, color: T.textMid, fontFamily: "'IBM Plex Mono', monospace",
          marginBottom: 6 }}>RETURN TIER</div>
        <div style={{ fontSize: 18, fontWeight: 700, fontFamily: "'IBM Plex Mono', monospace",
          color: profitPct >= 15 ? T.gold : profitPct >= 8 ? T.green : T.textMid }}>
          {profitPct >= 20 ? '🔥 AGGRESSIVE'
          : profitPct >= 12 ? '⚡ HIGH RETURN'
          : profitPct >= 7  ? '✅ GOOD RETURN'
          : '📊 MODERATE'}
        </div>
      </div>
    </div>
  );
}

function PositionCard({ pos, index }) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ background: T.card, border: `1px solid ${T.border}`, borderRadius: 12,
      overflow: 'hidden', transition: 'border-color 0.2s' }}
      onMouseEnter={e => e.currentTarget.style.borderColor = T.borderHi}
      onMouseLeave={e => e.currentTarget.style.borderColor = T.border}
    >
      <div onClick={() => setOpen(!open)} style={{ padding: '16px', cursor: 'pointer',
        display: 'flex', alignItems: 'center', gap: 12 }}>
        {/* Rank */}
        <div style={{ width: 32, height: 32, borderRadius: 8, flexShrink: 0,
          background: T.accentDim, border: `1px solid ${T.accent}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 13, fontWeight: 800, color: T.accent,
          fontFamily: "'IBM Plex Mono', monospace" }}>{index + 1}</div>

        {/* Symbol info */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 15, fontWeight: 800, color: T.text,
              fontFamily: "'IBM Plex Mono', monospace" }}>{pos.symbol}</span>
            <span style={{ fontSize: 9, padding: '2px 8px', borderRadius: 4, fontWeight: 700,
              background: T.greenDim, color: T.green,
              fontFamily: "'IBM Plex Mono', monospace" }}>
              BUY · {pos.confidence}%
            </span>
            {pos.atr_pct > 2 && (
              <span style={{ fontSize: 9, padding: '2px 8px', borderRadius: 4, fontWeight: 700,
                background: T.goldDim, color: T.gold,
                fontFamily: "'IBM Plex Mono', monospace" }}>
                ⚡ HIGH VOL {pos.atr_pct}%
              </span>
            )}
          </div>
          <div style={{ fontSize: 11, color: T.textMid, marginTop: 4 }}>
            {pos.shares} shares × ₹{fmt2(pos.entry_price)} = {fmtINR(pos.amount_invested)}
          </div>
        </div>

        {/* Profit highlight — the most important number */}
        <div style={{ textAlign: 'right', flexShrink: 0 }}>
          <div style={{ fontSize: 10, color: T.textDim, fontFamily: "'IBM Plex Mono', monospace",
            marginBottom: 3 }}>TARGET PROFIT</div>
          <div style={{ fontSize: 18, fontWeight: 800, color: T.green,
            fontFamily: "'IBM Plex Mono', monospace",
            textShadow: `0 0 12px ${T.greenGlow}` }}>
            +{fmtINR(pos.potential_profit)}
          </div>
          <div style={{ fontSize: 10, color: T.green, opacity: 0.7, marginTop: 2 }}>
            +{pos.profit_on_invested}% on invested
          </div>
        </div>

        <span style={{ color: T.textDim, fontSize: 12 }}>{open ? '▲' : '▼'}</span>
      </div>

      {open && (
        <div style={{ padding: '0 16px 16px', borderTop: `1px solid ${T.border}` }}>

          {/* Trade plan */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginTop: 12 }}>
            {[
              { label: 'BUY AT',    val: `₹${fmt2(pos.entry_price)}`, color: T.text },
              { label: 'SELL AT',   val: `₹${fmt2(pos.target)}`,      color: T.green,
                sub: `+${pos.profit_pct}% move` },
              { label: 'EXIT IF',   val: `₹${fmt2(pos.stop_loss)}`,   color: T.red,
                sub: `loss cut` },
            ].map(({ label, val, color, sub }) => (
              <div key={label} style={{ background: T.panel, borderRadius: 8,
                padding: '10px 12px', border: `1px solid ${T.border}` }}>
                <div style={{ fontSize: 8, color: T.textDim, letterSpacing: '0.1em',
                  fontFamily: "'IBM Plex Mono', monospace", marginBottom: 5 }}>{label}</div>
                <div style={{ fontSize: 14, fontWeight: 700, color,
                  fontFamily: "'IBM Plex Mono', monospace" }}>{val}</div>
                {sub && <div style={{ fontSize: 9, color, opacity: 0.7, marginTop: 2 }}>{sub}</div>}
              </div>
            ))}
          </div>

          {/* P&L boxes */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginTop: 8 }}>
            <div style={{ background: T.greenDim, borderRadius: 8, padding: '12px',
              border: `1px solid rgba(0,229,168,0.25)`, textAlign: 'center' }}>
              <div style={{ fontSize: 8, color: T.textDim, fontFamily: "'IBM Plex Mono', monospace",
                marginBottom: 6 }}>YOU MAKE</div>
              <div style={{ fontSize: 18, fontWeight: 800, color: T.green,
                fontFamily: "'IBM Plex Mono', monospace" }}>
                +{fmtINR(pos.potential_profit)}
              </div>
            </div>
            <div style={{ background: T.redDim, borderRadius: 8, padding: '12px',
              border: `1px solid rgba(255,61,90,0.2)`, textAlign: 'center' }}>
              <div style={{ fontSize: 8, color: T.textDim, fontFamily: "'IBM Plex Mono', monospace",
                marginBottom: 6 }}>MAX LOSS</div>
              <div style={{ fontSize: 18, fontWeight: 800, color: T.red,
                fontFamily: "'IBM Plex Mono', monospace" }}>
                -{fmtINR(pos.potential_loss)}
              </div>
            </div>
            <div style={{ background: T.accentDim, borderRadius: 8, padding: '12px',
              border: `1px solid rgba(123,108,255,0.2)`, textAlign: 'center' }}>
              <div style={{ fontSize: 8, color: T.textDim, fontFamily: "'IBM Plex Mono', monospace",
                marginBottom: 6 }}>R : R</div>
              <div style={{ fontSize: 18, fontWeight: 800, color: T.accent,
                fontFamily: "'IBM Plex Mono', monospace" }}>
                1 : {pos.rr_ratio}
              </div>
            </div>
          </div>

          {/* Why selected */}
          {pos.reasons?.length > 0 && (
            <div style={{ marginTop: 12, padding: '12px 14px', background: T.bg,
              borderRadius: 8, border: `1px solid ${T.border}` }}>
              <div style={{ fontSize: 9, color: T.textDim, letterSpacing: '0.1em',
                fontFamily: "'IBM Plex Mono', monospace", marginBottom: 8 }}>
                WHY THIS STOCK
              </div>
              {pos.reasons.map((r, i) => (
                <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 5,
                  alignItems: 'flex-start' }}>
                  <span style={{ color: T.green, fontSize: 11, flexShrink: 0 }}>✓</span>
                  <span style={{ fontSize: 11, color: T.textMid, lineHeight: 1.5 }}>{r}</span>
                </div>
              ))}
            </div>
          )}

          <div style={{ marginTop: 10, padding: '8px 12px', background: T.goldDim,
            border: `1px solid rgba(245,200,66,0.2)`, borderRadius: 7,
            fontSize: 10, color: T.gold, lineHeight: 1.5 }}>
            ⏱ Square off before <strong>3:20 PM IST</strong> — intraday only.
          </div>
        </div>
      )}
    </div>
  );
}

export default function CapitalAllocator() {
  const [capital,  setCapital]  = useState('');
  const [plan,     setPlan]     = useState(null);
  const [loading,  setLoading]  = useState(false);
  const [elapsed,  setElapsed]  = useState(0);
  const [error,    setError]    = useState(null);
  const timerRef = useRef(null);

  useEffect(() => {
    if (loading) {
      setElapsed(0);
      timerRef.current = setInterval(() => setElapsed(e => e + 1), 1000);
    } else {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [loading]);

  const analyze = useCallback(async () => {
    const amt = parseFloat(String(capital).replace(/,/g, ''));
    if (!amt || amt < 500) { setError('Minimum ₹500'); return; }
    setLoading(true); setError(null); setPlan(null);
    try {
      const res = await fetch(`${BASE}/api/allocate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ capital: amt }),
      });
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || `Error ${res.status}`);
      setPlan(await res.json());
    } catch (e) {
      setError(e.message || 'Backend not reachable. Start uvicorn.');
    } finally { setLoading(false); }
  }, [capital]);

  const displayAmt = parseFloat(String(capital).replace(/,/g, '')) || 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>

      {/* Input card */}
      <div style={{ background: T.panel, border: `1px solid ${T.border}`,
        borderRadius: 12, padding: 20 }}>

        <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.1em',
          color: T.textMid, fontFamily: "'IBM Plex Mono', monospace", marginBottom: 6 }}>
          💰 CAPITAL ALLOCATION — TARGET 10-20% RETURNS
        </div>
        <div style={{ fontSize: 11, color: T.textMid, marginBottom: 16, lineHeight: 1.7 }}>
          Scans <strong style={{ color: T.text }}>high-volatility NSE stocks</strong> matched to your capital.
          Small capital → cheap stocks with big % moves.
          Analysis takes 1–2 min for accuracy.
        </div>

        {/* Presets */}
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 14 }}>
          {PRESETS.map(p => (
            <button key={p.label}
              onClick={() => { setCapital(p.value.toString()); setError(null); setPlan(null); }}
              style={{
                padding: '5px 12px', borderRadius: 6, border: `1px solid ${displayAmt === p.value ? T.accent : T.border}`,
                background: displayAmt === p.value ? T.accentDim : T.bg,
                color: displayAmt === p.value ? T.accent : T.textMid,
                fontSize: 10, fontWeight: 700, cursor: 'pointer',
                fontFamily: "'IBM Plex Mono', monospace", transition: 'all 0.15s',
              }}>{p.label}</button>
          ))}
        </div>

        <div style={{ display: 'flex', gap: 10 }}>
          <div style={{ flex: 1, display: 'flex', alignItems: 'center',
            background: T.bg, borderRadius: 8, overflow: 'hidden',
            border: `1px solid ${error ? T.red : T.borderHi}` }}>
            <span style={{ padding: '0 14px', fontSize: 20, color: T.textMid,
              fontFamily: "'IBM Plex Mono', monospace" }}>₹</span>
            <input
              value={capital} disabled={loading}
              onChange={e => { setCapital(e.target.value); setError(null); setPlan(null); }}
              onKeyDown={e => e.key === 'Enter' && analyze()}
              placeholder="Enter amount — ₹500, ₹1000, ₹50000..."
              style={{ flex: 1, padding: '13px 6px', background: 'transparent',
                border: 'none', outline: 'none', color: T.text, fontSize: 15,
                fontFamily: "'IBM Plex Mono', monospace", fontWeight: 700 }}
            />
            {displayAmt > 0 && (
              <span style={{ padding: '0 14px', fontSize: 11, color: T.textDim,
                fontFamily: "'IBM Plex Mono', monospace", whiteSpace: 'nowrap' }}>
                {fmtINR(displayAmt)}
              </span>
            )}
          </div>
          <button onClick={analyze} disabled={!capital || loading} style={{
            padding: '13px 22px', borderRadius: 8, border: 'none',
            background: loading ? T.accentDim : T.accent, color: '#fff',
            fontWeight: 700, fontSize: 11, letterSpacing: '0.08em', cursor: 'pointer',
            fontFamily: "'IBM Plex Mono', monospace", whiteSpace: 'nowrap',
            display: 'flex', alignItems: 'center', gap: 8,
            opacity: (!capital || loading) ? 0.6 : 1,
          }}>
            {loading
              ? <><span style={{ width: 12, height: 12, border: '2px solid rgba(255,255,255,0.3)',
                  borderTopColor: '#fff', borderRadius: '50%', display: 'inline-block',
                  animation: 'spin 0.8s linear infinite' }} />ANALYZING</>
              : '📡 FIND TRADES'}
          </button>
        </div>

        {error && (
          <div style={{ marginTop: 10, padding: '9px 14px', background: T.redDim,
            border: `1px solid rgba(255,61,90,0.3)`, borderRadius: 7,
            color: T.red, fontSize: 11, fontFamily: "'IBM Plex Mono', monospace" }}>
            ⚠ {error}
          </div>
        )}
      </div>

      {loading && <ScanProgress elapsed={elapsed} />}

      {plan && !loading && (
        <>
          {plan.positions?.length === 0 ? (
            <div style={{ padding: '32px', textAlign: 'center', background: T.panel,
              border: `1px solid ${T.border}`, borderRadius: 12, lineHeight: 1.8 }}>
              <div style={{ fontSize: 30, marginBottom: 10 }}>📊</div>
              <div style={{ fontSize: 13, color: T.text, fontWeight: 600 }}>
                No high-return trades found
              </div>
              <div style={{ fontSize: 11, color: T.textMid, marginTop: 6 }}>
                {plan.message}
              </div>
            </div>
          ) : (
            <>
              {/* Big profit banner */}
              <ProfitBanner
                profit={plan.total_potential_profit}
                profitPct={plan.total_profit_pct}
                capital={plan.capital}
              />

              {/* Summary strip */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
                {[
                  { label: 'CAPITAL',   val: fmtINR(plan.capital),           color: T.text },
                  { label: 'DEPLOYED',  val: fmtINR(plan.total_deployed),    color: T.blue,
                    sub: `${plan.deployment_pct}%` },
                  { label: 'MAX LOSS',  val: `-${fmtINR(plan.total_potential_loss)}`, color: T.red,
                    sub: `${plan.max_risk_pct}% at risk` },
                  { label: 'PORTFOLIO RR', val: `1 : ${plan.portfolio_rr}`,
                    color: plan.portfolio_rr >= 2 ? T.green : T.gold },
                ].map(({ label, val, color, sub }) => (
                  <div key={label} style={{ background: T.panel, border: `1px solid ${T.border}`,
                    borderRadius: 10, padding: '12px 14px' }}>
                    <div style={{ fontSize: 8, color: T.textDim, letterSpacing: '0.1em',
                      fontFamily: "'IBM Plex Mono', monospace", marginBottom: 5 }}>{label}</div>
                    <div style={{ fontSize: 14, fontWeight: 700, color,
                      fontFamily: "'IBM Plex Mono', monospace" }}>{val}</div>
                    {sub && <div style={{ fontSize: 9, color: T.textDim, marginTop: 2 }}>{sub}</div>}
                  </div>
                ))}
              </div>

              {/* Position cards */}
              {plan.positions.map((pos, i) => (
                <PositionCard key={pos.symbol} pos={pos} index={i} />
              ))}

              <div style={{ fontSize: 10, color: T.textDim, textAlign: 'center',
                lineHeight: 1.8, padding: '0 8px' }}>
                ⚠ Algorithmic signals — not SEBI registered advice. Past performance ≠ future results.
                Always use a stop loss. Square off all positions before <strong>3:20 PM IST</strong>.
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
