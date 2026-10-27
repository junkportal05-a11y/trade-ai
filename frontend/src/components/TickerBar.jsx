import React from 'react';

import { T, DEFAULT_WATCHLIST, fmt, clr, sign } from '../theme';

export default function TickerBar({ prices, dataSource }) {
  const symbols = DEFAULT_WATCHLIST.map(w => w.symbol);
  return (
    <div style={{ background: T.surface, borderBottom: `1px solid ${T.border}`, overflow: 'hidden', height: 32, display: 'flex', alignItems: 'center', position: 'relative' }}>
      <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 40, background: `linear-gradient(90deg,${T.surface},transparent)`, zIndex: 1, pointerEvents: 'none' }} />
      <div style={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: 40, background: `linear-gradient(270deg,${T.surface},transparent)`, zIndex: 1, pointerEvents: 'none' }} />
      <div style={{ display: 'flex', gap: 0, padding: '0 40px', animation: 'marquee 120s linear infinite', whiteSpace: 'nowrap' }}>
        {[...symbols, ...symbols].map((sym, i) => {
          const p = prices[sym];
          const hasTick = !!p && p.price != null;
          const source = dataSource?.[sym];
          const isSimulated = hasTick && source === 'simulated';
          return (
            <span key={i} style={{ display: 'inline-flex', gap: 7, alignItems: 'center', fontSize: 11, fontFamily: "'IBM Plex Mono', monospace", padding: '0 20px', borderRight: `1px solid ${T.border}` }}>
              <span style={{ color: T.textMid, fontWeight: 600, letterSpacing: '0.05em', fontSize: 10 }}>{sym.replace('.NS', '')}</span>
              {hasTick ? (
                <>
                  <span style={{ color: T.text, fontWeight: 500 }}>₹{fmt(p.price)}</span>
                  <span style={{ color: (p?.changePct ?? 0) >= 0 ? T.green : T.red, fontSize: 10, background: (p?.changePct ?? 0) >= 0 ? T.greenDim : T.redDim, padding: '1px 5px', borderRadius: 3 }}>{sign(p?.changePct ?? 0)}{fmt(p?.changePct ?? 0, 2)}%</span>
                </>
              ) : (
                <>
                  <span style={{ color: T.textDim, fontWeight: 500 }}>—</span>
                  <span style={{ color: '#f5c842', fontSize: 9, background: 'rgba(245,200,66,0.12)', padding: '1px 4px', borderRadius: 3, fontFamily: "'IBM Plex Mono', monospace", fontWeight: 600 }}>SEED</span>
                </>
              )}
              {isSimulated && <span style={{ color: '#f5c842', fontSize: 9, background: 'rgba(245,200,66,0.12)', padding: '1px 4px', borderRadius: 3, fontFamily: "'IBM Plex Mono', monospace", fontWeight: 600, marginLeft: 4 }}>SIM</span>}
            </span>
          );
        })}
      </div>
      <style>{`@keyframes marquee { from { transform: translateX(0); } to { transform: translateX(-50%); } }`}</style>
    </div>
  );
}