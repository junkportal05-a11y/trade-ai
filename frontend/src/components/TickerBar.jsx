import React from 'react';
import { T, DEFAULT_WATCHLIST, fmt, sign } from '../theme';

export default function TickerBar({ prices = {}, dataSource = {} }) {
  const symbols = DEFAULT_WATCHLIST.map(w => w.symbol);
  
  return (
    <div style={{
      height: 32,
      borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
      background: '#000000',
      padding: '0 16px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      fontSize: 11,
      color: T.textMid,
      overflowX: 'auto',
      whiteSpace: 'nowrap',
      zIndex: 45,
      position: 'relative'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ position: 'relative', display: 'flex', width: 8, height: 8 }}>
            <span style={{
              position: 'absolute',
              display: 'inline-flex',
              width: '100%',
              height: '100%',
              borderRadius: '50%',
              background: T.accentAlt,
              opacity: 0.75,
              animation: 'ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite'
            }} />
            <span style={{
              position: 'relative',
              display: 'inline-flex',
              borderRadius: '50%',
              width: 8,
              height: 8,
              background: T.accentAlt
            }} />
          </span>
          <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', color: T.accentAlt, textTransform: 'uppercase' }}>
            NSE TICK FEED
          </span>
          <span style={{
            padding: '1px 5px',
            borderRadius: 3,
            background: T.goldDim,
            border: `1px solid ${T.borderHi}`,
            fontSize: 9,
            fontWeight: 700,
            color: T.gold,
            fontFamily: "'IBM Plex Mono', monospace"
          }}>
            SIMULATED
          </span>
        </div>

        <div style={{ height: 12, width: 1, background: 'rgba(255, 255, 255, 0.1)' }} />

        {/* Real Live Prices */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 18, fontFamily: "'IBM Plex Mono', monospace", fontSize: 11 }}>
          {symbols.map((sym) => {
            const p = prices?.[sym];
            const hasTick = !!p && p.price != null;
            const isUp = (p?.changePct ?? 0) >= 0;
            const cleanSym = sym.replace('.NS', '');
            return (
              <span key={sym} style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                <span style={{ color: T.textMid }}>{cleanSym}:</span>
                {hasTick ? (
                  <strong style={{ color: isUp ? T.accentAlt : T.red, fontWeight: 600 }}>
                    ₹{fmt(p.price)} ({sign(p.changePct)}{fmt(p.changePct, 2)}%)
                  </strong>
                ) : (
                  <span style={{ color: T.textDim }}>₹0.00</span>
                )}
              </span>
            );
          })}
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 14, fontSize: 10, color: T.textDim }}>
        <span>FEED: <strong style={{ color: T.accentAlt, fontFamily: "'IBM Plex Mono', monospace" }}>SYNCHRONIZED</strong></span>
        <span>LATENCY: <strong style={{ color: '#cbd5e1', fontFamily: "'IBM Plex Mono', monospace" }}>11ms</strong></span>
      </div>

      <style>{`
        @keyframes ping {
          75%, 100% {
            transform: scale(2);
            opacity: 0;
          }
        }
      `}</style>
    </div>
  );
}
