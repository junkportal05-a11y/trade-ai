import React from 'react';
import { T, fmt, clr, sign } from '../theme';

export default function PortfolioPanel({ prices, portfolio, cash }) {
  let stockValue = 0, totalCost = 0;
  const positions = portfolio.map(pos => {
    const price = prices[pos.symbol]?.price ?? pos.avgCost;
    const value = price * pos.shares;
    const cost = pos.avgCost * pos.shares;
    const pnl = value - cost;
    const pnlPct = cost > 0 ? ((value - cost) / cost) * 100 : 0;
    stockValue += value; totalCost += cost;
    return { ...pos, price, value, pnl, pnlPct };
  });
  const totalValue = stockValue + cash;
  const totalPnl = stockValue - totalCost;
  const totalPct = totalCost > 0 ? (totalPnl / totalCost) * 100 : 0;
  const C = 157.08;
  const slices = [];
  let acc = 0;
  if (totalValue > 0) {
    const cashWeight = cash / totalValue;
    slices.push({ label: 'Cash', value: cash, color: T.blue, weight: cashWeight, dashOffset: C - (acc * C) });
    acc += cashWeight;
  }
  const COLORS = ['#7b6cff', '#00e5a8', '#ff9f43', '#9b5de5', '#f5c842', '#ff3d5a', '#ff4da6'];
  positions.forEach((pos, idx) => {
    if (totalValue > 0 && pos.value > 0) {
      const weight = pos.value / totalValue;
      slices.push({ label: pos.symbol.replace('.NS', ''), value: pos.value, color: COLORS[idx % COLORS.length], weight, dashOffset: C - (acc * C) });
      acc += weight;
    }
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div style={{ padding: '14px 16px 10px', borderBottom: `1px solid ${T.border}` }}>
        <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.12em', color: T.textMid, fontFamily: "'IBM Plex Mono', monospace" }}>PORTFOLIO</span>
      </div>
      <div style={{ padding: '14px 16px', borderBottom: `1px solid ${T.border}`, background: 'rgba(255,255,255,0.015)' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          <div>
            <div style={{ fontSize: 9, color: T.textDim, marginBottom: 4, fontFamily: "'IBM Plex Mono', monospace" }}>NET WORTH</div>
            <div style={{ fontSize: 15, fontWeight: 700, color: T.text, fontFamily: "'IBM Plex Mono', monospace' }}>₹{fmt(totalValue)}</div>
            <div style={{ fontSize: 9, color: clr(totalPnl), marginTop: 2, fontFamily: "'IBM Plex Mono', monospace" }}>{sign(totalPnl)}₹{fmt(Math.abs(totalPnl))} ({sign(totalPct)}{fmt(totalPct, 2)}%)</div>
          </div>
          <div style={{ borderLeft: `1px solid ${T.border}`, paddingLeft: 10 }}>
            <div style={{ fontSize: 9, color: T.textDim, marginBottom: 4, fontFamily: "'IBM Plex Mono', monospace" }}>AVAILABLE CASH</div>
            <div style={{ fontSize: 15, fontWeight: 700, color: T.blue, fontFamily: "'IBM Plex Mono', monospace" }}>₹{fmt(cash)}</div>
            <div style={{ fontSize: 9, color: T.textDim, marginTop: 2 }}>Stocks: ₹{fmt(stockValue)}</div>
          </div>
        </div>
      </div>
      {slices.length > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '12px 16px', borderBottom: `1px solid ${T.border}`, gap: 20, background: 'rgba(255,255,255,0.005)' }}>
          <svg width="68" height="68" viewBox="0 0 80 80" style={{ transform: 'rotate(-90deg)', flexShrink: 0 }}>
            <circle cx="40" cy="40" r="25" stroke={T.borderHi} strokeWidth="8" fill="transparent" />
            {slices.map((s, idx) => (
              <circle key={idx} cx="40" cy="40" r="25" stroke={s.color} strokeWidth="8" fill="transparent" strokeDasharray={`${s.weight * C} ${C}`} strokeDashoffset={-s.dashOffset + C} style={{ transition: 'stroke-dashoffset 0.6s ease' }} />
            ))}
          </svg>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, flex: 1, minWidth: 0 }}>
            {slices.map((s, idx) => (
              <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 9, fontFamily: "'IBM Plex Mono', monospace" }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: s.color, display: 'inline-block', flexShrink: 0 }} />
                <span style={{ color: T.textMid, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.label}</span>
                <span style={{ color: T.text, fontWeight: 600, flexShrink: 0 }}>{(s.weight * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>
        </div>
      )}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {positions.length === 0 ? <div style={{ padding: '30px 16px', textAlign: 'center', color: T.textDim, fontSize: 11, fontFamily: "'IBM Plex Mono', monospace" }}>NO POSITIONS HELD</div> :
        positions.map(pos => (
          <div key={pos.symbol} style={{ padding: '10px 16px', borderBottom: `1px solid ${T.border}` }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
              <span style={{ fontSize: 11, fontWeight: 700, color: T.text, fontFamily: "'IBM Plex Mono', monospace" }}>{pos.symbol.replace('.NS', '')}</span>
              <span style={{ fontSize: 11, color: T.text, fontFamily: "'IBM Plex Mono', monospace" }}>₹{fmt(pos.value)}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ fontSize: 10, color: T.textDim }}>{pos.shares} × ₹{fmt(pos.avgCost)}</span>
              <span style={{ fontSize: 10, color: clr(pos.pnl), fontFamily: "'IBM Plex Mono', monospace" }}>{sign(pos.pnl)}₹{fmt(Math.abs(pos.pnl))}</span>
            </div>
            <div style={{ height: 2, background: T.border, borderRadius: 2, marginTop: 6, overflow: 'hidden' }}>
              <div style={{ height: '100%', width: `${Math.min(100, Math.abs(pos.pnlPct) * 3)}%`, background: clr(pos.pnl), transition: 'width 0.6s ease', borderRadius: 2 }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}