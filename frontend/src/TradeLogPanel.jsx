import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE_URL, apiFetch } from './api';
import { useBotWebSocket } from './hooks/useBotWebSocket';

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
const fmtTime = (ts) => new Date(ts).toLocaleTimeString('en-IN', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });

export default function TradeLogPanel({ maxItems = 50 }) {
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('ALL'); // ALL | BUY | SELL | OPEN | CLOSED

  const { botData, connected } = useBotWebSocket();

  useEffect(() => {
    setTrades(botData.trades || []);
    setLoading(!connected && (!botData.trades || botData.trades.length === 0));
  }, [botData.trades, connected]);

  const filteredTrades = trades.filter(t => {
    if (filter === 'ALL') return true;
    if (filter === 'BUY' || filter === 'SELL') return t.side?.toUpperCase() === filter;
    if (filter === 'OPEN') return t.status === 'OPEN';
    if (filter === 'CLOSED') return t.status === 'CLOSED';
    return true;
  });

  return (
    <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 12, padding: 16, display: 'flex', flexDirection: 'column', gap: 12, minHeight: 300 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: `1px solid ${T.border}`, paddingBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>📋</span>
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', color: T.accentAlt, ...mono }}>TRADE LOG</div>
            <div style={{ fontSize: 12, fontWeight: 700, color: '#fff' }}>Live Bot Decisions</div>
          </div>
        </div>

        {/* Filter Tabs */}
        <div style={{ display: 'flex', gap: 4, background: T.panel, border: `1px solid ${T.border}`, borderRadius: 6, padding: 2 }}>
          {['ALL', 'BUY', 'SELL', 'OPEN', 'CLOSED'].map(f => (
            <button key={f} onClick={() => setFilter(f)} style={{
              padding: '4px 10px', borderRadius: 4, border: 'none', cursor: 'pointer',
              background: filter === f ? T.accent : 'transparent',
              color: filter === f ? '#fff' : T.textMid,
              fontSize: 9, fontWeight: 700, letterSpacing: '0.04em', ...mono,
              transition: 'all 0.15s',
            }}>{f}</button>
          ))}
        </div>
      </div>

      {/* Trade List */}
      <div style={{ flex: 1, overflowY: 'auto', minHeight: 200 }}>
        {loading && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 100, color: T.textDim, ...mono }}>
            <span style={{ width: 16, height: 16, border: `2px solid ${T.border}`, borderTopColor: T.accent, borderRadius: '50%', animation: 'spin 0.8s linear infinite', marginRight: 8 }} />
            Loading trade log...
          </div>
        )}

        {!loading && filteredTrades.length === 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: 120, gap: 8, color: T.textDim, ...mono }}>
            <span style={{ fontSize: 24 }}>📋</span>
            <span style={{ fontSize: 10 }}>No trades {filter !== 'ALL' ? `(${filter})` : ''} yet</span>
            <span style={{ fontSize: 9, color: T.textDim }}>Bot will log decisions here when running</span>
          </div>
        )}

        {!loading && filteredTrades.length > 0 && (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
            <thead>
              <tr style={{ color: T.textDim, borderBottom: `1px solid ${T.border}` }}>
                <th style={{ padding: '8px 4px', textAlign: 'left', fontWeight: 700 }}>TIME</th>
                <th style={{ padding: '8px 4px', textAlign: 'left', fontWeight: 700 }}>SIDE</th>
                <th style={{ padding: '8px 4px', textAlign: 'left', fontWeight: 700 }}>SYMBOL</th>
                <th style={{ padding: '8px 4px', textAlign: 'left', fontWeight: 700 }}>QTY</th>
                <th style={{ padding: '8px 4px', textAlign: 'left', fontWeight: 700 }}>PRICE</th>
                <th style={{ padding: '8px 4px', textAlign: 'left', fontWeight: 700 }}>STATUS</th>
                <th style={{ padding: '8px 4px', textAlign: 'left', fontWeight: 700 }}>P&L</th>
                <th style={{ padding: '8px 4px', textAlign: 'left', fontWeight: 700 }}>REASON</th>
              </tr>
            </thead>
            <tbody>
              {filteredTrades.map((trade, idx) => (
                <tr key={trade.id || idx} style={{ borderBottom: `1px solid ${T.border}30`, animation: 'fadeIn 0.3s ease' }}>
                  <td style={{ padding: '8px 4px', color: T.textMid, ...mono }}>{fmtTime(trade.timestamp)}</td>
                  <td style={{ padding: '8px 4px' }}>
                    <span style={{
                      display: 'inline-flex', alignItems: 'center', gap: 4,
                      padding: '2px 8px', borderRadius: 4,
                      background: trade.side === 'buy' ? T.greenDim : T.redDim,
                      color: trade.side === 'buy' ? T.green : T.red,
                      fontWeight: 700, fontSize: 9, ...mono
                    }}>
                      {trade.side === 'buy' ? '▲' : '▼'} {trade.side?.toUpperCase()}
                    </span>
                  </td>
                  <td style={{ padding: '8px 4px', color: '#fff', fontWeight: 700, ...mono }}>{trade.symbol?.replace('.NS', '')}</td>
                  <td style={{ padding: '8px 4px', ...mono }}>{trade.qty}</td>
                  <td style={{ padding: '8px 4px', ...mono }}>₹{fmt(trade.price)}</td>
                  <td style={{ padding: '8px 4px' }}>
                    <span style={{
                      padding: '2px 6px', borderRadius: 3, fontSize: 8, fontWeight: 700, ...mono,
                      background: trade.status === 'OPEN' ? T.blueDim : T.goldDim,
                      color: trade.status === 'OPEN' ? T.blue : T.gold,
                    }}>{trade.status}</span>
                  </td>
                  <td style={{ padding: '8px 4px', ...mono }}>
                    {trade.pnl !== undefined && trade.pnl !== null ? (
                      <span style={{ color: trade.pnl >= 0 ? T.green : T.red, fontWeight: 700 }}>
                        {trade.pnl >= 0 ? '+' : ''}₹{fmt(Math.abs(trade.pnl))}
                      </span>
                    ) : (
                      <span style={{ color: T.textDim }}>—</span>
                    )}
                  </td>
                  <td style={{ padding: '8px 4px', color: T.textMid, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {trade.reason || '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes fadeIn { from { opacity:0; transform:translateY(-4px); } to { opacity:1; transform:translateY(0); } }
      `}</style>
    </div>
  );
}