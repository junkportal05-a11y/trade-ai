/**
 * PerformancePanel.jsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Full-width backtesting & signal history dashboard.
 * Drop into frontend/src/PerformancePanel.jsx
 */

import { useState, useEffect, useCallback } from "react";

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

const fmt2 = (n) => n == null ? '—' : Number(n).toFixed(2);
const pct  = (n) => n == null ? '—' : `${n > 0 ? '+' : ''}${fmt2(n)}%`;
const clr  = (v) => v > 0 ? T.green : v < 0 ? T.red : T.textMid;

const STATUS_META = {
  HIT_TARGET: { label: 'TARGET HIT',  bg: T.greenDim, color: T.green,   dot: T.green  },
  HIT_STOP:   { label: 'STOP HIT',    bg: T.redDim,   color: T.red,     dot: T.red    },
  PENDING:    { label: 'ACTIVE',       bg: T.goldDim,  color: T.gold,    dot: T.gold   },
  EXPIRED:    { label: 'EXPIRED',      bg: T.grayDim,  color: T.gray,    dot: T.gray   },
  CLOSED:     { label: 'CLOSED',       bg: T.blueDim,  color: T.blue,    dot: T.blue   },
};

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
      borderRadius: 10, padding: '16px 20px', flex: 1, minWidth: 120,
    }}>
      <div style={{ fontSize: 9, color: T.textDim, letterSpacing: '0.12em',
        fontFamily: "'IBM Plex Mono', monospace", marginBottom: 8 }}>{label}</div>
      <div style={{ fontSize: big ? 28 : 22, fontWeight: 700,
        color: color || T.text, fontFamily: "'IBM Plex Mono', monospace",
        letterSpacing: '-0.02em', lineHeight: 1 }}>{value}</div>
      {sub && <div style={{ fontSize: 10, color: T.textMid, marginTop: 6 }}>{sub}</div>}
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

export default function PerformancePanel() {
  const [stats,   setStats]   = useState(null);
  const [history, setHistory] = useState([]);
  const [filter,  setFilter]  = useState('ALL');
  const [loading, setLoading] = useState(true);
  const [resetting, setResetting] = useState(false);

  const load = useCallback(async () => {
    try {
      const [sRes, hRes] = await Promise.all([
        fetch(`${BASE}/api/backtest/stats`),
        fetch(`${BASE}/api/backtest/history?limit=200`),
      ]);
      if (sRes.ok) setStats(await sRes.json());
      if (hRes.ok) {
        const d = await hRes.json();
        setHistory(d.history || []);
      }
    } catch {
      // backend offline — show empty state
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 15000); // refresh every 15s
    return () => clearInterval(t);
  }, [load]);

  const reset = async () => {
    if (!confirm("Clear all signal history? This cannot be undone.")) return;
    setResetting(true);
    try {
      await fetch(`${BASE}/api/backtest/reset`, { method: 'POST' });
      await load();
    } finally {
      setResetting(false);
    }
  };

  const filtered = filter === 'ALL'
    ? history
    : history.filter(h => h.status === filter);

  if (loading) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
        gap: 12, color: T.textMid, fontFamily: "'IBM Plex Mono', monospace", fontSize: 12 }}>
        <span style={{ width: 14, height: 14, border: `2px solid ${T.border}`,
          borderTopColor: T.accent, borderRadius: '50%', display: 'inline-block',
          animation: 'spin 0.7s linear infinite' }} />
        LOADING PERFORMANCE DATA
      </div>
    );
  }

  const noData = !stats || stats.total === 0;

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px',
      display: 'flex', flexDirection: 'column', gap: 20, background: T.bg }}>

      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <div style={{ fontSize: 16, fontWeight: 700, color: T.text,
            fontFamily: "'IBM Plex Mono', monospace", letterSpacing: '0.04em' }}>
            SIGNAL PERFORMANCE
          </div>
          <div style={{ fontSize: 11, color: T.textMid, marginTop: 4 }}>
            Automated backtesting — signals logged every 60s during market hours
          </div>
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <div style={{ fontSize: 10, color: T.textDim, fontFamily: "'IBM Plex Mono', monospace" }}>
            AUTO-REFRESH 15s
          </div>
          <button onClick={reset} disabled={resetting || noData} style={{
            padding: '8px 16px', background: T.redDim, border: `1px solid rgba(255,61,90,0.3)`,
            borderRadius: 6, color: T.red, fontSize: 10, fontWeight: 700,
            cursor: noData ? 'not-allowed' : 'pointer', opacity: noData ? 0.4 : 1,
            fontFamily: "'IBM Plex Mono', monospace", letterSpacing: '0.06em',
            transition: 'all 0.2s',
          }}>
            {resetting ? 'CLEARING...' : '⟳ RESET DB'}
          </button>
        </div>
      </div>

      {noData ? (
        /* Empty state */
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center',
          justifyContent: 'center', gap: 16, padding: '60px 0' }}>
          <div style={{ fontSize: 40 }}>📡</div>
          <div style={{ fontSize: 14, fontWeight: 700, color: T.text,
            fontFamily: "'IBM Plex Mono', monospace" }}>NO TRADES LOGGED YET</div>
          <div style={{ fontSize: 12, color: T.textMid, textAlign: 'center', maxWidth: 400, lineHeight: 1.6 }}>
            The background scanner logs BUY/SELL signals automatically every 60 seconds
            during NSE market hours (9:15 AM – 3:30 PM IST). Check back after the market opens.
          </div>
          <div style={{ padding: '12px 20px', background: T.panel, border: `1px solid ${T.border}`,
            borderRadius: 8, fontSize: 11, color: T.textMid,
            fontFamily: "'IBM Plex Mono', monospace" }}>
            Backend must be running: <span style={{ color: T.accent }}>uvicorn main:app --reload</span>
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
            <KpiCard label="ACTIVE NOW" value={stats.pending}
              color={stats.pending > 0 ? T.gold : T.textMid}
              sub="monitoring live" />
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
            <div style={{ maxHeight: 420, overflowY: 'auto' }}>
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

          {/* Disclaimer */}
          <div style={{ fontSize: 10, color: T.textDim, textAlign: 'center',
            lineHeight: 1.6, padding: '0 20px' }}>
            Backtesting uses algorithmic signals only. Past performance does not guarantee future results.
            Signals are for educational purposes — not financial advice.
          </div>
        </>
      )}
    </div>
  );
}
