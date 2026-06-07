import React, { useState, useEffect, useRef } from 'react';

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
  greenGlow:  'rgba(0,229,168,0.25)',
  red:        '#ff3d5a',
  redDim:     'rgba(255,61,90,0.1)',
  redGlow:    'rgba(255,61,90,0.25)',
  blue:       '#4da6ff',
  blueDim:    'rgba(77,166,255,0.1)',
  blueGlow:   'rgba(77,166,255,0.2)',
  gold:       '#f5c842',
  accent:     '#7b6cff',
  accentAlt:  '#9b5de5',
  accentDim:  'rgba(123,108,255,0.12)',
};

const mono = { fontFamily: "'IBM Plex Mono', monospace" };
const fmt = (n, d = 2) => n == null ? '—' : Number(n).toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d });

export default function OrderBookPanel({ symbol, price }) {
  const [bids, setBids] = useState([]);
  const [asks, setAsks] = useState([]);
  const [trades, setTrades] = useState([]);
  const prevPriceRef = useRef(price);

  // Initialize and update order book rows on price change
  useEffect(() => {
    if (!price) return;
    
    // NSE tick size is 0.05
    const tickSize = 0.05;
    const cleanSymbol = symbol.replace('.NS', '');

    // Generate 5 Ask levels (above current price, sorted descending for display: high to low asks)
    const newAsks = [];
    for (let i = 5; i >= 1; i--) {
      newAsks.push({
        price: price + tickSize * i,
        qty: Math.floor(Math.random() * 2500) + 100,
        orders: Math.floor(Math.random() * 12) + 1
      });
    }

    // Generate 5 Bid levels (below current price, sorted descending: high to low bids)
    const newBids = [];
    for (let i = 1; i <= 5; i++) {
      newBids.push({
        price: price - tickSize * i,
        qty: Math.floor(Math.random() * 2500) + 100,
        orders: Math.floor(Math.random() * 12) + 1
      });
    }

    setAsks(newAsks);
    setBids(newBids);

    // If the price actually changed, append a trade to Time & Sales
    if (price !== prevPriceRef.current) {
      const side = Math.random() > 0.45 ? 'BUY' : 'SELL';
      const qty = (Math.floor(Math.random() * 10) + 1) * 10 * (Math.random() > 0.8 ? 5 : 1);
      const now = new Date();
      const timeStr = now.toLocaleTimeString('en-IN', { hour12: false });
      
      setTrades(prev => [
        { id: Math.random().toString(36).substring(2, 9), time: timeStr, price, qty, side },
        ...prev.slice(0, 7) // keep last 8 entries
      ]);
      prevPriceRef.current = price;
    }
  }, [price, symbol]);

  // Seed initial trades if log is empty
  useEffect(() => {
    if (!price || trades.length > 0) return;
    const initialTrades = [];
    const tickSize = 0.05;
    for (let i = 0; i < 8; i++) {
      const tradeTime = new Date(Date.now() - i * 1500);
      initialTrades.push({
        id: Math.random().toString(36).substring(2, 9),
        time: tradeTime.toLocaleTimeString('en-IN', { hour12: false }),
        price: price + (Math.random() > 0.5 ? tickSize : -tickSize) * Math.floor(Math.random() * 3),
        qty: (Math.floor(Math.random() * 8) + 1) * 10,
        side: Math.random() > 0.5 ? 'BUY' : 'SELL'
      });
    }
    setTrades(initialTrades);
  }, [price]);

  // Sum total sizes to calculate percentage bars
  const maxBidQty = bids.reduce((max, b) => Math.max(max, b.qty), 1);
  const maxAskQty = asks.reduce((max, a) => Math.max(max, a.qty), 1);
  const maxDepthQty = Math.max(maxBidQty, maxAskQty);

  const totalBidVol = bids.reduce((sum, b) => sum + b.qty, 0);
  const totalAskVol = asks.reduce((sum, a) => sum + a.qty, 0);
  const totalVol = totalBidVol + totalAskVol;
  const bidRatio = totalVol > 0 ? (totalBidVol / totalVol) * 100 : 50;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', borderTop: `1px solid ${T.border}`, background: T.surface }}>
      {/* Header */}
      <div style={{ padding: '10px 16px', borderBottom: `1px solid ${T.border}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.12em', color: T.textMid, ...mono }}>L2 MARKET DEPTH</span>
        <span style={{ fontSize: 9, color: T.textDim, ...mono }}>{symbol.replace('.NS', '')}</span>
      </div>

      {/* L2 Table */}
      <div style={{ padding: '8px 12px', flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, justifyContent: 'space-between' }}>
        
        {/* Asks (Sells) - High to Low */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {asks.map((ask, idx) => {
            const pct = (ask.qty / maxDepthQty) * 100;
            return (
              <div key={idx} style={{ position: 'relative', display: 'flex', justifyContent: 'space-between', height: 18, alignItems: 'center', fontSize: 10, ...mono, padding: '0 4px' }}>
                <div style={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: `${pct}%`, background: T.redDim, zIndex: 0, transition: 'width 0.3s ease' }} />
                <span style={{ color: T.red, zIndex: 1, fontWeight: 600 }}>₹{fmt(ask.price)}</span>
                <span style={{ color: T.text, zIndex: 1 }}>{ask.qty}</span>
                <span style={{ color: T.textDim, zIndex: 1, width: 20, textAlign: 'right' }}>{ask.orders}</span>
              </div>
            );
          })}
        </div>

        {/* Spread / Bid-Ask Line */}
        <div style={{ padding: '4px 4px', borderTop: `1px solid ${T.border}`, borderBottom: `1px solid ${T.border}`, background: T.panelAlt, display: 'flex', justifyContent: 'space-between', fontSize: 10, ...mono, margin: '4px 0' }}>
          <span style={{ color: T.textMid }}>SPREAD:</span>
          <span style={{ color: T.text, fontWeight: 700 }}>₹0.05</span>
          <span style={{ color: T.textMid }}>({((0.05 / (price || 1)) * 100).toFixed(3)}%)</span>
        </div>

        {/* Bids (Buys) - High to Low */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {bids.map((bid, idx) => {
            const pct = (bid.qty / maxDepthQty) * 100;
            return (
              <div key={idx} style={{ position: 'relative', display: 'flex', justifyContent: 'space-between', height: 18, alignItems: 'center', fontSize: 10, ...mono, padding: '0 4px' }}>
                <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: `${pct}%`, background: T.greenDim, zIndex: 0, transition: 'width 0.3s ease' }} />
                <span style={{ color: T.green, zIndex: 1, fontWeight: 600 }}>₹{fmt(bid.price)}</span>
                <span style={{ color: T.text, zIndex: 1 }}>{bid.qty}</span>
                <span style={{ color: T.textDim, zIndex: 1, width: 20, textAlign: 'right' }}>{bid.orders}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Buy/Sell Volume Ratio indicator bar */}
      <div style={{ padding: '0 12px 10px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 8, color: T.textDim, ...mono, marginBottom: 3 }}>
          <span>BUY VOL: {totalBidVol} ({bidRatio.toFixed(0)}%)</span>
          <span>SELL VOL: {totalAskVol} ({(100 - bidRatio).toFixed(0)}%)</span>
        </div>
        <div style={{ height: 3, background: T.red, borderRadius: 2, display: 'flex', overflow: 'hidden' }}>
          <div style={{ width: `${bidRatio}%`, background: T.green, height: '100%', transition: 'width 0.5s ease' }} />
        </div>
      </div>

      {/* Time & Sales */}
      <div style={{ display: 'flex', flexDirection: 'column', height: 120, borderTop: `1px solid ${T.border}`, overflow: 'hidden' }}>
        <div style={{ padding: '6px 12px', borderBottom: `1px solid ${T.border}`, display: 'flex', justifyContent: 'space-between', background: T.panelAlt }}>
          <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.08em', color: T.textMid, ...mono }}>TIME & SALES</span>
          <span style={{ fontSize: 8, color: T.textDim, ...mono }}>LIVE STREAM</span>
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: '4px 12px', display: 'flex', flexDirection: 'column', gap: 2 }}>
          {trades.map(trade => (
            <div key={trade.id} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, ...mono, height: 14, alignItems: 'center', animation: 'fadeIn 0.2s ease' }}>
              <span style={{ color: T.textDim }}>{trade.time}</span>
              <span style={{ color: trade.side === 'BUY' ? T.green : T.red, fontWeight: 600 }}>₹{fmt(trade.price)}</span>
              <span style={{ color: T.text }}>{trade.qty}</span>
              <span style={{ color: trade.side === 'BUY' ? T.green : T.red, fontSize: 8, padding: '0px 3px', background: trade.side === 'BUY' ? T.greenDim : T.redDim, borderRadius: 2 }}>
                {trade.side}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
