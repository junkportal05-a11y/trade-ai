import React, { useState, useEffect } from 'react';
import { useLivePrices, isNSEMarketOpen } from '../hooks/useMarketData';
import { useHealthCheck } from '../hooks/useHealthCheck';
import SystemHealthModal from './SystemHealthModal';
import { T, fmt, clr, sign, PRIMARY_TABS, SECONDARY_TABS, TAB_META } from '../theme';

export default function Header({ connected, view, onViewChange, isMobile, netWorth, cash, stockValue, totalPnl, totalPct, selectedSymbol, prices }) {
  const [clock, setClock] = useState(() => new Date().toLocaleTimeString('en-IN', { hour12: true }));
  useEffect(() => { const t = setInterval(() => setClock(new Date().toLocaleTimeString('en-IN', { hour12: true })), 1000); return () => clearInterval(t); }, []);
  const [showMore, setShowMore] = useState(false);
  const [showHealthModal, setShowHealthModal] = useState(false);
  const health = useHealthCheck(20000);
  const p = prices[selectedSymbol];
  const price = p?.price ?? 0;
  const pct = p?.changePct ?? 0;
  const isUp = pct >= 0;

  return (
    <div style={{ padding: '0 16px', height: 54, display: 'flex', alignItems: 'center', gap: 16, borderBottom: `1px solid ${T.border}`, background: T.surface, flexShrink: 0 }}>
      <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 13, fontWeight: 700, letterSpacing: '0.12em', whiteSpace: 'nowrap', background: `linear-gradient(135deg, ${T.accent}, ${T.accentAlt})`, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', flexShrink: 0 }}>
        ◈ ApexTrade Bot Engine
      </div>
      {!isMobile && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ display: 'flex', background: T.bg, borderRadius: 6, padding: 2, border: `1px solid ${T.border}`, flexShrink: 0 }}>
            {PRIMARY_TABS.map(v => {
              const meta = TAB_META[v] || { icon: '', label: v };
              const isActive = view === v;
              return (
                <button key={v} onClick={() => onViewChange(v)} style={{ padding: '4px 12px', borderRadius: 4, border: 'none', cursor: 'pointer',
                  background: isActive ? T.accentDim : 'transparent', color: isActive ? T.accentAlt : T.textDim,
                  fontSize: 9, fontWeight: 700, letterSpacing: '0.08em', fontFamily: "'Inter', sans-serif", transition: 'all 0.2s', }}>{meta.icon} {meta.label}</button>
              );
            })}
          </div>
          {SECONDARY_TABS.length > 0 && (
            <div style={{ position: 'relative' }}>
              <button onClick={() => setShowMore(s => !s)} style={{ padding: '4px 10px', borderRadius: 6, border: `1px solid ${T.border}`, background: T.bg, cursor: 'pointer',
                color: SECONDARY_TABS.some(t => view === t) ? T.accentAlt : T.textDim, fontSize: 9, fontWeight: 700, letterSpacing: '0.08em', fontFamily: "'Inter', sans-serif" }}>⋯ MORE</button>
              {showMore && (
                <>
                  <div onClick={() => setShowMore(false)} style={{ position: 'fixed', inset: 0, zIndex: 99 }} />
                  <div style={{ position: 'absolute', top: '100%', right: 0, marginTop: 6, background: T.surface, border: `1px solid ${T.border}`, borderRadius: 8, padding: 4, zIndex: 100, minWidth: 150, boxShadow: '0 8px 24px rgba(0,0,0,0.5)' }}>
                    {SECONDARY_TABS.map(v => {
                      const meta = TAB_META[v] || { icon: '', label: v };
                      const isActive = view === v;
                      return (
                        <button key={v} onClick={() => { onViewChange(v); setShowMore(false); }} style={{ display: 'block', width: '100%', textAlign: 'left', padding: '8px 10px', borderRadius: 6, border: 'none', cursor: 'pointer',
                          background: isActive ? T.accentDim : 'transparent', color: isActive ? T.accentAlt : T.text, fontSize: 10, fontWeight: 700, fontFamily: "'Inter', sans-serif", }}>{meta.icon} {meta.label}</button>
                      );
                    })}
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      )}
      <div style={{ width: 1, height: 22, background: T.border, flexShrink: 0 }} />
      {!isMobile && view === 'CHART' && selectedSymbol && (
        <>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, minWidth: 0, flexShrink: 0 }}>
            <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, fontWeight: 700, color: T.textMid, letterSpacing: '0.06em' }}>{selectedSymbol.replace('.NS', '')}</span>
            <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 18, fontWeight: 700, color: T.text, letterSpacing: '-0.02em' }}>₹{fmt(price)}</span>
            <span style={{ fontSize: 10, color: clr(pct), background: isUp ? T.blueDim : T.redDim, border: `1px solid ${isUp ? T.blueGlow : T.redGlow}`, padding: '1px 6px', borderRadius: 4, fontFamily: "'IBM Plex Mono', monospace" }}>
              {sign(pct)}{fmt(pct, 2)}%
            </span>
          </div>
          <div style={{ width: 1, height: 22, background: T.border, flexShrink: 0 }} />
        </>
      )}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, minWidth: 0 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <span style={{ fontSize: 8, fontWeight: 700, color: T.textDim, letterSpacing: '0.04em' }}>PORTFOLIO VALUE</span>
          <span style={{ fontSize: 13, fontWeight: 700, color: '#fff', fontFamily: "'IBM Plex Mono', monospace" }}>₹{fmt(netWorth)}</span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <span style={{ fontSize: 8, fontWeight: 700, color: T.textDim, letterSpacing: '0.04em' }}>TOTAL P&L</span>
          <span style={{ fontSize: 11, fontWeight: 700, color: clr(totalPnl), fontFamily: "'IBM Plex Mono', monospace" }}>{sign(totalPnl)}₹{fmt(Math.abs(totalPnl))} ({sign(totalPct)}{fmt(totalPct, 2)}%)</span>
        </div>
        {!isMobile && (
          <>
            <div style={{ width: 1, height: 20, background: T.border, flexShrink: 0 }} />
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <span style={{ fontSize: 8, fontWeight: 700, color: T.textDim, letterSpacing: '0.04em' }}>AVAILABLE CASH</span>
              <span style={{ fontSize: 11, fontWeight: 700, color: T.blue, fontFamily: "'IBM Plex Mono', monospace" }}>₹{fmt(cash)}</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <span style={{ fontSize: 8, fontWeight: 700, color: T.textDim, letterSpacing: '0.04em' }}>STOCKS HOLDINGS</span>
              <span style={{ fontSize: 11, fontWeight: 700, color: T.textMid, fontFamily: "'IBM Plex Mono', monospace" }}>₹{fmt(stockValue)}</span>
            </div>
          </>
        )}
      </div>
      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 16 }}>
        {!isMobile && <span style={{ fontSize: 10, color: T.textDim, fontFamily: "'IBM Plex Mono', monospace", letterSpacing: '0.06em' }}>{clock} UTC+5:30</span>}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button
            onClick={() => setShowHealthModal(true)}
            title="Click to view Subsystem Health (DB, Broker, Workers, AI)"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              background: 'rgba(255, 255, 255, 0.03)',
              border: `1px solid ${T.border}`,
              padding: '3px 8px',
              borderRadius: 6,
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = T.borderHi; e.currentTarget.style.background = 'rgba(255, 255, 255, 0.06)'; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = T.border; e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)'; }}
          >
            <div style={{ width: 6, height: 6, borderRadius: '50%', background: !connected ? T.red : (isNSEMarketOpen() ? T.green : T.gold),
              boxShadow: connected && isNSEMarketOpen() ? `0 0 8px ${T.greenGlow}` : 'none', animation: connected && isNSEMarketOpen() ? 'pulse 2s ease-in-out infinite' : 'none' }} />
            <span style={{ fontSize: 10, color: !connected ? T.red : (isNSEMarketOpen() ? T.green : T.gold), fontFamily: "'IBM Plex Mono', monospace", letterSpacing: '0.08em' }}>
              {!connected ? 'OFFLINE' : (isNSEMarketOpen() ? 'LIVE' : 'CLOSED')}
            </span>
          </button>
        </div>
      </div>

      <SystemHealthModal
        isOpen={showHealthModal}
        onClose={() => setShowHealthModal(false)}
        health={health}
        onRefresh={health.refresh}
      />
    </div>
  );
}