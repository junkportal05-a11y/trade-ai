import React from 'react';
import { Briefcase, Clock, Bell, Lightbulb, Sparkles, RefreshCw } from 'lucide-react';
import Label from './Label';
import Input from './TextInput';
import { T, fmt, clr, sign, SEED_PRICES } from '../theme';

export default function BottomConsole({ prices, portfolio, cash, openOrders, onCancelOrder, priceAlerts, onDeleteAlert, aiRecommendation, aiRecommendationLoading, aiRecommendationError, aiRecommendationSource, selected, onExecuteOrder, onViewChange, consoleTab, setConsoleTab, onRefreshAnalyst }) {
  const totalStockValue = portfolio.reduce((sum, pos) => {
    const price = prices[pos.symbol]?.price ?? SEED_PRICES[pos.symbol] ?? pos.avgCost;
    return sum + (price * pos.shares);
  }, 0);
  const netWorth = totalStockValue + cash;

  return (
    <div style={{ height: 220, borderTop: `1px solid ${T.border}`, background: T.surface, display: 'flex', flexDirection: 'column', flexShrink: 0, overflow: 'hidden' }}>
      <div style={{ display: 'flex', alignItems: 'center', borderBottom: `1px solid ${T.border}`, background: T.panelAlt, flexShrink: 0, padding: '0 16px', height: 38 }}>
        <div style={{ display: 'flex', gap: 2 }}>
          {[['POSITIONS', 'POSITIONS', Briefcase], ['ORDERS', 'OPEN ORDERS', Clock], ['ALERTS', 'PRICE ALERTS', Bell], ['AI', 'AI ANALYST', Lightbulb]].map(([tab, label, Icon]) => (
            <button key={tab} onClick={() => setConsoleTab(tab)} style={{ padding: '0 12px', background: 'transparent', border: 'none', cursor: 'pointer',
              color: consoleTab === tab ? T.accent : T.textMid, fontSize: 9.5, fontWeight: 700, letterSpacing: '0.04em', fontFamily: "'Inter', sans-serif",
              borderBottom: `2px solid ${consoleTab === tab ? T.accent : 'transparent'}`, height: 38, transition: 'all 0.15s', display: 'inline-flex', alignItems: 'center', gap: 5 }}>
              <Icon size={11} />{label}</button>
          ))}
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 16, fontSize: 10, fontFamily: "'IBM Plex Mono', monospace" }}>
          <div><span style={{ color: T.textDim }}>NET WORTH:</span> <strong style={{ color: '#fff' }}>₹{fmt(netWorth)}</strong></div>
          <div><span style={{ color: T.textDim }}>CASH:</span> <strong style={{ color: T.blue }}>₹{fmt(cash)}</strong></div>
        </div>
      </div>
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 16px', position: 'relative' }}>
        {consoleTab === 'POSITIONS' && (
          <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            {portfolio.length === 0 ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 1, color: T.textDim, fontSize: 11, fontFamily: "'IBM Plex Mono', monospace" }}>NO ACTIVE POSITIONS HELD</div>
            ) : (
              <div style={{ flex: 1, overflowY: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 11 }}>
                  <thead><tr style={{ color: T.textDim, borderBottom: `1px solid ${T.border}` }}>
                    <th style={{ paddingBottom: 6, fontWeight: 700 }}>SYMBOL</th><th style={{ paddingBottom: 6, fontWeight: 700 }}>SHARES</th>
                    <th style={{ paddingBottom: 6, fontWeight: 700 }}>AVG COST</th><th style={{ paddingBottom: 6, fontWeight: 700 }}>LAST PRICE</th>
                    <th style={{ paddingBottom: 6, fontWeight: 700 }}>MARKET VALUE</th><th style={{ paddingBottom: 6, fontWeight: 700 }}>P&L</th>
                    <th style={{ paddingBottom: 6, fontWeight: 700, textAlign: 'right' }}>ACTION</th>
                  </tr></thead>
                  <tbody>
                    {portfolio.map(pos => {
                      const price = prices[pos.symbol]?.price ?? SEED_PRICES[pos.symbol] ?? pos.avgCost;
                      const value = price * pos.shares;
                      const cost = pos.avgCost * pos.shares;
                      const pnl = value - cost;
                      const pnlPct = cost > 0 ? (pnl / cost) * 100 : 0;
                      return (
                        <tr key={pos.symbol} style={{ borderBottom: `1px solid ${T.border}` }}>
                          <td style={{ padding: '8px 0', fontWeight: 700, color: '#fff', fontFamily: "'IBM Plex Mono', monospace" }}>{pos.symbol.replace('.NS', '')}</td>
                          <td style={{ padding: '8px 0', fontFamily: "'IBM Plex Mono', monospace" }}>{pos.shares}</td>
                          <td style={{ padding: '8px 0', fontFamily: "'IBM Plex Mono', monospace" }}>₹{fmt(pos.avgCost)}</td>
                          <td style={{ padding: '8px 0', fontFamily: "'IBM Plex Mono', monospace" }}>₹{fmt(price)}</td>
                          <td style={{ padding: '8px 0', fontFamily: "'IBM Plex Mono', monospace" }}>₹{fmt(value)}</td>
                          <td style={{ padding: '8px 0', color: clr(pnl), fontWeight: 700, fontFamily: "'IBM Plex Mono', monospace" }}>{sign(pnl)}₹{fmt(Math.abs(pnl))} ({sign(pnlPct)}{fmt(pnlPct, 2)}%)</td>
                          <td style={{ padding: '8px 0', textAlign: 'right' }}>
                            <button onClick={() => onExecuteOrder({ side: 'sell', symbol: pos.symbol, type: 'market', qty: pos.shares.toString(), price })} style={{ padding: '3px 8px', background: 'rgba(255, 61, 90, 0.06)', border: `1px solid rgba(255, 61, 90, 0.25)`, borderRadius: 4, color: T.red, fontSize: 9, fontWeight: 700, cursor: 'pointer', fontFamily: "'Inter', sans-serif", transition: 'all 0.15s' }}>MARKET SELL CLOSE</button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
        {consoleTab === 'ORDERS' && (
          <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            {openOrders.length === 0 ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 1, color: T.textDim, fontSize: 11, fontFamily: "'IBM Plex Mono', monospace" }}>NO OPEN LIMIT ORDERS</div>
            ) : (
              <div style={{ flex: 1, overflowY: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 11 }}>
                  <thead><tr style={{ color: T.textDim, borderBottom: `1px solid ${T.border}` }}>
                    <th style={{ paddingBottom: 6, fontWeight: 700 }}>SIDE</th><th style={{ paddingBottom: 6, fontWeight: 700 }}>SYMBOL</th>
                    <th style={{ paddingBottom: 6, fontWeight: 700 }}>QTY</th><th style={{ paddingBottom: 6, fontWeight: 700 }}>LIMIT PRICE</th>
                    <th style={{ paddingBottom: 6, fontWeight: 700 }}>ORDER TYPE</th><th style={{ paddingBottom: 6, fontWeight: 700, textAlign: 'right' }}>ACTION</th>
                  </tr></thead>
                  <tbody>
                    {openOrders.map(o => (
                      <tr key={o.id} style={{ borderBottom: `1px solid ${T.border}` }}>
                        <td style={{ padding: '8px 0', fontWeight: 700, color: o.side === 'buy' ? T.green : T.red, fontFamily: "'IBM Plex Mono', monospace" }}>{o.side.toUpperCase()}</td>
                        <td style={{ padding: '8px 0', fontWeight: 700, color: '#fff', fontFamily: "'IBM Plex Mono', monospace" }}>{o.symbol.replace('.NS', '')}</td>
                        <td style={{ padding: '8px 0', fontFamily: "'IBM Plex Mono', monospace" }}>{o.qty}</td>
                        <td style={{ padding: '8px 0', fontFamily: "'IBM Plex Mono', monospace" }}>₹{fmt(o.limitPrice)}</td>
                        <td style={{ padding: '8px 0', color: T.textMid }}>LIMIT (PAPER)</td>
                        <td style={{ padding: '8px 0', textAlign: 'right' }}>
                          <button onClick={() => onCancelOrder(o.id)} style={{ padding: '3px 8px', background: 'rgba(255, 61, 90, 0.06)', border: `1px solid rgba(255, 61, 90, 0.25)`, borderRadius: 4, color: T.red, fontSize: 9, fontWeight: 700, cursor: 'pointer', fontFamily: "'Inter', sans-serif" }}>CANCEL ORDER</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
        {consoleTab === 'ALERTS' && (
          <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            {priceAlerts.length === 0 ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 1, color: T.textDim, fontSize: 11, fontFamily: "'IBM Plex Mono', monospace" }}>NO ACTIVE PRICE ALERTS</div>
            ) : (
              <div style={{ flex: 1, overflowY: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 11 }}>
                  <thead><tr style={{ color: T.textDim, borderBottom: `1px solid ${T.border}` }}>
                    <th style={{ paddingBottom: 6, fontWeight: 700 }}>SYMBOL</th><th style={{ paddingBottom: 6, fontWeight: 700 }}>TRIGGER CONDITION</th>
                    <th style={{ paddingBottom: 6, fontWeight: 700 }}>TARGET LEVEL</th><th style={{ paddingBottom: 6, fontWeight: 700 }}>LAST PRICE</th>
                    <th style={{ paddingBottom: 6, fontWeight: 700, textAlign: 'right' }}>ACTION</th>
                  </tr></thead>
                  <tbody>
                    {priceAlerts.map(a => {
                      const price = prices[a.symbol]?.price ?? SEED_PRICES[a.symbol] ?? 0;
                      return (
                        <tr key={a.id} style={{ borderBottom: `1px solid ${T.border}` }}>
                          <td style={{ padding: '8px 0', fontWeight: 700, color: '#fff', fontFamily: "'IBM Plex Mono', monospace" }}>{a.symbol.replace('.NS', '')}</td>
                          <td style={{ padding: '8px 0', color: a.condition === 'above' ? T.green : T.red }}>
                            {a.condition === 'above' ? 'Crosses Above (≥)' : 'Drops Below (≤)'}</td>
                          <td style={{ padding: '8px 0', fontWeight: 600, fontFamily: "'IBM Plex Mono', monospace" }}>₹{fmt(a.targetPrice, 1)}</td>
                          <td style={{ padding: '8px 0', fontFamily: "'IBM Plex Mono', monospace" }}>₹{fmt(price)}</td>
                          <td style={{ padding: '8px 0', textAlign: 'right' }}>
                            <button onClick={() => onDeleteAlert(a.id)} style={{ padding: '3px 8px', background: 'rgba(255, 61, 90, 0.06)', border: `1px solid rgba(255, 61, 90, 0.25)`, borderRadius: 4, color: T.red, fontSize: 9, fontWeight: 700, cursor: 'pointer', fontFamily: "'Inter', sans-serif" }}>REMOVE</button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
        {consoleTab === 'AI' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, height: '100%', boxSizing: 'border-box' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: `1px solid ${T.border}`, paddingBottom: 4 }}>
              <div style={{ fontSize: 9.5, fontWeight: 700, color: T.accentAlt, display: 'flex', alignItems: 'center', gap: 6 }}><Lightbulb size={11} /> AI QUANT ANALYST: {selected.replace('.NS', '')}</div>
              {aiRecommendationLoading && <span style={{ display: 'inline-block', width: 10, height: 10, border: `1.5px solid ${T.border}`, borderTopColor: T.accentAlt, borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />}
              {!aiRecommendationLoading && !aiRecommendationError && aiRecommendationSource && (
                <span style={{ fontSize: 8.5, color: T.textDim, fontFamily: "'IBM Plex Mono', monospace", letterSpacing: '0.06em', border: `1px solid ${T.border}`, borderRadius: 3, padding: '1px 5px', whiteSpace: 'nowrap' }}>
                  {aiRecommendationSource === 'heuristic' ? 'source: local heuristic fallback' : /^[a-z0-9 _-]+$/i.test(aiRecommendationSource) ? `source: ${aiRecommendationSource}` : 'source: backend'}
                </span>
              )}
            </div>
            <div style={{ fontSize: 11.5, color: T.text, lineHeight: 1.5, overflowY: 'auto', flex: 1, paddingRight: 4 }}>
              {aiRecommendationLoading ? <span style={{ color: T.textDim }}>Running technical scan and generating insights...</span> : aiRecommendationError ? (
                <span style={{ color: '#ff5f6d' }}>
                  {aiRecommendationError}{' '}
                  {onRefreshAnalyst && (
                    <button onClick={onRefreshAnalyst} style={{ padding: '2px 8px', background: 'rgba(255, 95, 109, 0.08)', border: '1px solid rgba(255, 95, 109, 0.3)', borderRadius: 4, color: '#ff5f6d', fontSize: 9, fontWeight: 700, cursor: 'pointer', fontFamily: "'Inter', sans-serif", letterSpacing: '0.04em', transition: 'all 0.2s' }}>RETRY</button>
                  )}
                </span>
              ) : (aiRecommendation || "Select a ticker from the watchlist to fetch a quick technical recommendation.")}
            </div>
            {!aiRecommendationLoading && aiRecommendation && (
              <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
                <button onClick={() => onViewChange('PREDICTIONS')} style={{ padding: '3px 8px', background: 'rgba(245, 200, 66, 0.06)', border: `1px solid rgba(245, 200, 66, 0.25)`, borderRadius: 5, color: '#f5c842', fontSize: 9, fontWeight: 700, cursor: 'pointer', fontFamily: "'Inter', sans-serif", letterSpacing: '0.04em', transition: 'all 0.2s', display: 'inline-flex', alignItems: 'center', gap: 4 }}><Sparkles size={10} /> LOG SYSTEM PREDICTION</button>
                {onRefreshAnalyst && (
                  <button onClick={onRefreshAnalyst} style={{ padding: '3px 8px', background: 'rgba(77, 166, 255, 0.06)', border: `1px solid rgba(77, 166, 255, 0.25)`, borderRadius: 5, color: T.blue, fontSize: 9, fontWeight: 700, cursor: 'pointer', fontFamily: "'Inter', sans-serif", letterSpacing: '0.04em', transition: 'all 0.2s', display: 'inline-flex', alignItems: 'center', gap: 4 }}><RefreshCw size={10} /> REFRESH</button>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}