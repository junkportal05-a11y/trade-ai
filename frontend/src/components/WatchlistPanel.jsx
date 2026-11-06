import React, { useState } from 'react';
import { Star } from 'lucide-react';
import { T, DEFAULT_WATCHLIST, SEED_PRICES, fmt, clr, sign } from '../theme';
export default function WatchlistPanel({ prices, selected, onSelect, favorites = [], onToggleFavorite }) {
  const [searchQuery, setSearchQuery] = useState('');
  const filtered = DEFAULT_WATCHLIST.filter(w => w.symbol.toLowerCase().includes(searchQuery.toLowerCase()) || w.name.toLowerCase().includes(searchQuery.toLowerCase()) || (w.sector && w.sector.toLowerCase().includes(searchQuery.toLowerCase())));
  const sorted = [...filtered].sort((a, b) => { const aF = favorites.includes(a.symbol), bF = favorites.includes(b.symbol); if (aF && !bF) return -1; if (!aF && bF) return 1; return 0; });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div style={{ padding: '12px 14px 8px', borderBottom: `1px solid ${T.border}`, display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.12em', color: T.textMid }}>WATCHLIST</span>
          <span style={{ fontSize: 9, color: T.textDim, fontFamily: "'IBM Plex Mono', monospace" }}>{sorted.length} SYMBOLS</span>
        </div>
        <input type="text" placeholder="Search watchlist..." value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
          style={{ width: '100%', background: T.bg, border: `1px solid ${T.border}`, borderRadius: 6, color: T.text, fontSize: 11, padding: '5px 8px', outline: 'none' }}
          onFocus={e => e.target.style.borderColor = T.accent} onBlur={e => e.target.style.borderColor = T.border} />
      </div>
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {sorted.length === 0 ? <div style={{ padding: '20px 14px', fontSize: 11, color: T.textDim, textAlign: 'center' }}>No matching symbols</div> :
        sorted.map(({ symbol, name, sector }) => {
          const p = prices[symbol], price = p?.price ?? SEED_PRICES[symbol] ?? 0, pct = p?.changePct ?? 0, isUp = pct >= 0, isSel = selected === symbol, isFav = favorites.includes(symbol);
          return (
            <div key={symbol} onClick={() => onSelect(symbol)} style={{ padding: '10px 14px', cursor: 'pointer', transition: 'background 0.15s', background: isSel ? T.goldDim : 'transparent', borderLeft: `2px solid ${isSel ? T.accent : 'transparent'}`, borderBottom: `1px solid ${T.border}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <button onClick={e => { e.stopPropagation(); onToggleFavorite(symbol); }} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, fontSize: 12, color: isFav ? T.gold : T.textDim }} aria-label={isFav ? `Remove ${symbol} from favorites` : `Add ${symbol} to favorites`}><Star size={12} fill={isFav ? T.gold : 'none'} /></button>
                    <span style={{ fontSize: 11, fontWeight: 700, color: isSel ? T.blue : T.text, letterSpacing: '0.02em', fontFamily: "'IBM Plex Mono', monospace", overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{symbol.replace('.NS', '')}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4 }}>
                    <span style={{ fontSize: 9, color: T.textDim }}>{name}</span>
                    {sector && <span style={{ fontSize: 8, background: T.panel, color: T.textMid, padding: '1px 4px', borderRadius: 3, fontWeight: 600 }}>{sector}</span>}
                  </div>
                </div>
                <div style={{ textAlign: 'right', flexShrink: 0 }}>
                  <div style={{ fontSize: 11, color: T.text, fontFamily: "'IBM Plex Mono', monospace" }}>₹{fmt(price)}</div>
                  <div style={{ fontSize: 9, color: clr(pct), marginTop: 4, background: isUp ? T.greenDim : T.redDim, padding: '1px 4px', borderRadius: 3, fontFamily: "'IBM Plex Mono', monospace", display: 'inline-block' }}>{sign(pct)}{fmt(pct, 2)}%</div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}