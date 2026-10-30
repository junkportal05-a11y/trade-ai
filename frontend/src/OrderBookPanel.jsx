import React, { useState, useEffect, useRef } from 'react';
import { T, mono } from './theme';

const fmt = (n, d = 2) => n == null ? '—' : Number(n).toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d });

export default function OrderBookPanel({ symbol, price }) {
  const [bids, setBids] = useState([]);
  const [asks, setAsks] = useState([]);
  const [trades, setTrades] = useState([]);
  const prevPriceRef = useRef(price);

  // L2 Feed from AngelOne is not yet implemented.
  // Order book mock data generation has been removed.
  useEffect(() => {
    // Left intentionally blank until WebSocket L2 depth is available
    setAsks([]);
    setBids([]);
    setTrades([]);
  }, [price, symbol]);

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
