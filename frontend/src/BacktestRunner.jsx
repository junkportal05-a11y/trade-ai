import React, { useState, useCallback } from 'react';
import { API_BASE_URL, apiFetch } from './api';
import { formatError } from './utils/formatError';

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
};

const mono = { fontFamily: "'IBM Plex Mono', monospace" };
const fmt = (n, d = 2) => n == null ? '—' : Number(n).toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d });
const fmtPct = (n) => n == null ? '—' : `${n >= 0 ? '+' : ''}${Number(n).toFixed(2)}%`;

const DEFAULT_SYMBOLS = [
  'RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS', 'ICICIBANK.NS',
  'SBIN.NS', 'BHARTIARTL.NS', 'ITC.NS', 'KOTAKBANK.NS', 'LT.NS',
];

export default function BacktestRunner({ onResults }) {
  const [symbol, setSymbol] = useState('RELIANCE.NS');
  const [startDate, setStartDate] = useState('2024-01-01');
  const [endDate, setEndDate] = useState('2024-12-31');
  const [strategy, setStrategy] = useState('intraday_momentum');
  const [capital, setCapital] = useState('100000');
  const [stopATR, setStopATR] = useState('1.5');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const res = await apiFetch('/api/backtest/run', {
        method: 'POST',
        body: JSON.stringify({
          symbol,
          start_date: startDate,
          end_date: endDate,
          strategy,
          capital: parseFloat(capital),
          stop_atr: parseFloat(stopATR),
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(formatError(data.detail || data, `HTTP ${res.status}`));
      }

      const data = await res.json();
      setResults(data);
      onResults?.(data);
    } catch (e) {
      setError(formatError(e));
    } finally {
      setLoading(false);
    }
  };

  const retPct = results?.total_return_pct ?? results?.total_pnl_pct ?? 0;
  const maxDd = results?.max_drawdown_pct ?? results?.max_drawdown ?? 0;
  const winRateVal = results?.win_rate ?? 0;
  const sharpeVal = results?.sharpe_ratio ?? 0;
  const profitFactorVal = results?.profit_factor ?? 0;

  const metricCards = results ? [
    { label: 'TOTAL RETURN', value: fmtPct(retPct), color: retPct >= 0 ? T.green : T.red },
    { label: 'WIN RATE', value: `${winRateVal.toFixed(1)}%`, color: winRateVal >= 50 ? T.green : winRateVal >= 40 ? T.gold : T.red },
    { label: 'MAX DRAWDOWN', value: `${maxDd.toFixed(2)}%`, color: T.red },
    { label: 'SHARPE RATIO', value: sharpeVal.toFixed(2), color: sharpeVal >= 1.5 ? T.green : sharpeVal >= 1 ? T.gold : T.red },
    { label: 'TOTAL TRADES', value: (results.total_trades ?? 0).toString(), color: T.accent },
    { label: 'PROFIT FACTOR', value: profitFactorVal.toFixed(2), color: profitFactorVal >= 1.5 ? T.green : profitFactorVal >= 1 ? T.gold : T.red },
  ] : [];

  return (
    <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 12, padding: 16, display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: `1px solid ${T.border}`, paddingBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>⏱️</span>
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', color: T.accentAlt, ...mono }}>BACKTEST ENGINE</div>
            <div style={{ fontSize: 12, fontWeight: 700, color: '#fff' }}>Historical Truth Engine</div>
          </div>
        </div>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
          <div>
            <label style={{ display: 'block', fontSize: 10, color: T.textDim, ...mono, marginBottom: 4 }}>SYMBOL</label>
            <select value={symbol} onChange={e => setSymbol(e.target.value)} style={{ width: '100%', padding: '8px 10px', background: T.bg, border: `1px solid ${T.borderHi}`, borderRadius: 6, color: T.text, fontSize: 11, ...mono }}>
              {DEFAULT_SYMBOLS.map(s => <option key={s} value={s}>{s.replace('.NS', '')}</option>)}
            </select>
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 10, color: T.textDim, ...mono, marginBottom: 4 }}>STRATEGY</label>
            <select value={strategy} onChange={e => setStrategy(e.target.value)} style={{ width: '100%', padding: '8px 10px', background: T.bg, border: `1px solid ${T.borderHi}`, borderRadius: 6, color: T.text, fontSize: 11, ...mono }}>
              <option value="intraday_momentum">Intraday Momentum</option>
              <option value="mean_reversion">Mean Reversion</option>
              <option value="breakout_volume">Breakout Volume</option>
              <option value="scalper_rsi">RSI Scalper</option>
              <option value="swing_trend">Swing Trend Follower</option>
            </select>
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 10, color: T.textDim, ...mono, marginBottom: 4 }}>START DATE</label>
            <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} style={{ width: '100%', padding: '8px 10px', background: T.bg, border: `1px solid ${T.borderHi}`, borderRadius: 6, color: T.text, fontSize: 11, ...mono }} />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 10, color: T.textDim, ...mono, marginBottom: 4 }}>END DATE</label>
            <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} style={{ width: '100%', padding: '8px 10px', background: T.bg, border: `1px solid ${T.borderHi}`, borderRadius: 6, color: T.text, fontSize: 11, ...mono }} />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 10, color: T.textDim, ...mono, marginBottom: 4 }}>CAPITAL (₹)</label>
            <input type="number" value={capital} onChange={e => setCapital(e.target.value)} min="10000" step="10000" style={{ width: '100%', padding: '8px 10px', background: T.bg, border: `1px solid ${T.borderHi}`, borderRadius: 6, color: T.text, fontSize: 11, ...mono }} />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 10, color: T.textDim, ...mono, marginBottom: 4 }}>STOP ATR MULT</label>
            <input type="number" value={stopATR} onChange={e => setStopATR(e.target.value)} min="0.5" max="3" step="0.1" style={{ width: '100%', padding: '8px 10px', background: T.bg, border: `1px solid ${T.borderHi}`, borderRadius: 6, color: T.text, fontSize: 11, ...mono }} />
          </div>
        </div>

        <button type="submit" disabled={loading} style={{
          padding: '12px 24px', borderRadius: 8, border: 'none',
          background: loading ? T.accentDim : T.accent, color: '#fff',
          fontWeight: 700, fontSize: 11, letterSpacing: '0.08em', cursor: loading ? 'not-allowed' : 'pointer',
          fontFamily: "'IBM Plex Mono', monospace", display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
        }}>
          {loading ? '⟳ RUNNING...' : '▶ RUN BACKTEST'}
        </button>

        {error && (
          <div style={{ padding: '10px 12px', background: T.redDim, border: `1px solid ${T.red}40`, borderRadius: 6, color: T.red, fontSize: 10, ...mono }}>
            {error}
          </div>
        )}
      </form>

      {/* Results */}
      {results && (
        <div style={{ borderTop: `1px solid ${T.border}`, paddingTop: 16, animation: 'fadeIn 0.3s ease' }}>
          <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', color: T.accentAlt, ...mono, marginBottom: 12 }}>
            RESULTS — {symbol.replace('.NS', '')} | {startDate} to {endDate}
          </div>

          {/* Key Metrics */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 12, marginBottom: 16 }}>
            {metricCards.map((m, i) => (
              <div key={i} style={{ background: T.panel, border: `1px solid ${T.border}`, borderRadius: 8, padding: '12px', textAlign: 'center' }}>
                <div style={{ fontSize: 8, fontWeight: 700, color: T.textDim, letterSpacing: '0.08em', ...mono, marginBottom: 6 }}>{m.label}</div>
                <div style={{ fontSize: 20, fontWeight: 700, color: m.color, ...mono }}>{m.value}</div>
              </div>
            ))}
          </div>

          {/* Trade List */}
          {results.trades && results.trades.length > 0 && (
            <div style={{ background: T.panel, border: `1px solid ${T.border}`, borderRadius: 8, overflow: 'hidden' }}>
              <div style={{ padding: '10px 12px', borderBottom: `1px solid ${T.border}`, fontSize: 9, fontWeight: 700, color: T.textDim, letterSpacing: '0.08em', ...mono }}>
                TRADE LOG ({results.trades.length} trades)
              </div>
              <div style={{ overflowX: 'auto', maxHeight: 300, overflowY: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 10 }}>
                  <thead>
                    <tr style={{ color: T.textDim, borderBottom: `1px solid ${T.border}` }}>
                      <th style={{ padding: '8px 10px', textAlign: 'left' }}>DATE</th>
                      <th style={{ padding: '8px 10px', textAlign: 'left' }}>SIDE</th>
                      <th style={{ padding: '8px 10px', textAlign: 'right' }}>ENTRY</th>
                      <th style={{ padding: '8px 10px', textAlign: 'right' }}>EXIT</th>
                      <th style={{ padding: '8px 10px', textAlign: 'right' }}>QTY</th>
                      <th style={{ padding: '8px 10px', textAlign: 'right' }}>P&L</th>
                      <th style={{ padding: '8px 10px', textAlign: 'right' }}>P&L %</th>
                      <th style={{ padding: '8px 10px', textAlign: 'left' }}>STATUS</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.trades.slice(0, 50).map((t, i) => (
                      <tr key={i} style={{ borderBottom: `1px solid ${T.border}30` }}>
                        <td style={{ padding: '8px 10px', color: T.textMid, ...mono }}>{t.entry_date}</td>
                        <td style={{ padding: '8px 10px' }}>
                          <span style={{
                            padding: '2px 6px', borderRadius: 3, fontSize: 8, fontWeight: 700, ...mono,
                            background: t.side === 'BUY' ? T.greenDim : T.redDim,
                            color: t.side === 'BUY' ? T.green : T.red,
                          }}>{t.side}</span>
                        </td>
                        <td style={{ padding: '8px 10px', textAlign: 'right', ...mono }}>₹{fmt(t.entry_price)}</td>
                        <td style={{ padding: '8px 10px', textAlign: 'right', ...mono }}>₹{fmt(t.exit_price)}</td>
                        <td style={{ padding: '8px 10px', textAlign: 'right', ...mono }}>{t.qty}</td>
                        <td style={{ padding: '8px 10px', textAlign: 'right', color: t.pnl >= 0 ? T.green : T.red, fontWeight: 700, ...mono }}>
                          {t.pnl >= 0 ? '+' : ''}₹{fmt(Math.abs(t.pnl))}
                        </td>
                        <td style={{ padding: '8px 10px', textAlign: 'right', color: t.pnl_pct >= 0 ? T.green : T.red, ...mono }}>
                          {fmtPct(t.pnl_pct)}
                        </td>
                        <td style={{ padding: '8px 10px' }}>
                          <span style={{
                            padding: '2px 6px', borderRadius: 3, fontSize: 8, fontWeight: 700, ...mono,
                            background: t.status === 'WIN' ? T.greenDim : t.status === 'LOSS' ? T.redDim : T.goldDim,
                            color: t.status === 'WIN' ? T.green : t.status === 'LOSS' ? T.red : T.gold,
                          }}>{t.status}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {results.trades.length > 50 && (
                <div style={{ padding: '8px 12px', color: T.textDim, fontSize: 9, textAlign: 'center', borderTop: `1px solid ${T.border}` }}>
                  Showing 50 of {results.trades.length} trades
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <style>{`
        @keyframes fadeIn { from { opacity:0; transform:translateY(4px); } to { opacity:1; transform:translateY(0); } }
      `}</style>
    </div>
  );
}