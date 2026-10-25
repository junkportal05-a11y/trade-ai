import React from 'react';
import { useLivePrices, isNSEMarketOpen } from '../hooks/useMarketData';

import { T, DEFAULT_WATCHLIST, SEED_PRICES, fmt, clr, sign } from '../theme';

export default function TickerBar({ prices, dataSource }) {
  const symbols = DEFAULT_WATCHLIST.map(w => w.symbol);
  return (
    <div style={{ background: T.surface, borderBottom: `1px solid ${T.border}`, overflow: 'hidden', height: 32, display: 'flex', alignItems: 'center', position: 'relative' }}>
      <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 40, background: `linear-gradient(90deg,${T.surface},transparent)`, zIndex: 1, pointerEvents: 'none' }} />
      <div style={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: 40, background: `linear-gradient(270deg,${T.surface},transparent)`, zIndex: 1, pointerEvents: 'none' }} />
      <div style={{ display: 'flex', gap: 0, padding: '0 40px', animation: 'marquee 120s linear infinite', whiteSpace: 'nowrap' }}>
        {[...symbols, ...symbols].map((sym, i) => {
          const p = prices[sym];
          const price = p?.price ?? SEED_PRICES[sym] ?? 0;
          const pct = p?.changePct ?? 0;
          const isUp = pct >= 0;
          const source = dataSource?.[sym];
          const isSimulated = source === 'simulated';
          return (
            <span key={i} style={{ display: 'inline-flex', gap: 7, alignItems: 'center', fontSize: 11, fontFamily: "'IBM Plex Mono', monospace", padding: '0 20px', borderRight: `1px solid ${T.border}` }}>
              <span style={{ color: T.textMid, fontWeight: 600, letterSpacing: '0.05em', fontSize: 10 }}>{sym.replace('.NS', '')}</span>
              <span style={{ color: T.text, fontWeight: 500 }}>₹{fmt(price)}</span>
              <span style={{ color: isUp ? T.green : T.red, fontSize: 10, background: isUp ? T.greenDim : T.redDim, padding: '1px 5px', borderRadius: 3 }}>{sign(pct)}{fmt(pct, 2)}%</span>
              {isSimulated && <span style={{ color: T.gold, fontSize: 9, background: T.goldDim, padding: '1px 4px', borderRadius: 3, fontFamily: "'IBM Plex Mono', monospace", fontWeight: 600, marginLeft: 4 }}>SIM</span>}
            </span>
          );
        })}
      </div>
      <style>{`@keyframes marquee { from { transform: translateX(0); } to { transform: translateX(-50%); } }`}</style>
    </div>
  );
}