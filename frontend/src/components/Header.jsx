import React, { useEffect, useMemo, useState } from 'react';
import { Home, Bot, TrendingUp, Radio, Sparkles, BarChart3, BookOpen, ShieldCheck, Activity, Search, Zap, Settings, HelpCircle } from 'lucide-react';
import SystemHealthModal from './SystemHealthModal';
import { useHealthCheck } from '../hooks/useHealthCheck';
import { T, fmt, clr, sign, PRIMARY_TABS, SECONDARY_TABS, TAB_META } from '../theme';

const ICON_MAP = { Home, Bot, TrendingUp, Radio, Sparkles, BarChart3, BookOpen, ShieldCheck, Settings, HelpCircle };

function getMarketSession(now = new Date()) {
  const ist = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));
  const day = ist.getDay();
  const minutes = ist.getHours() * 60 + ist.getMinutes();
  if (day === 0 || day === 6) {
    return { label: 'CLOSED', color: T.red, live: false };
  }
  if (minutes >= 9 * 60 && minutes < 9 * 60 + 15) {
    return { label: 'PRE-MARKET', color: '#f5c842', live: false };
  }
  if (minutes >= 9 * 60 + 15 && minutes <= 15 * 60 + 30) {
    return { label: 'NSE OPEN', color: T.green, live: true };
  }
  return { label: 'CLOSED', color: T.red, live: false };
}

const PILL_TRANSITION = 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)';

function NavButton({ tab, active, onClick }) {
  const meta = TAB_META[tab] || { icon: 'Home', label: tab };
  const Icon = ICON_MAP[meta.icon] || Home;
  return (
    <button
      onClick={onClick}
      aria-current={active ? 'page' : undefined}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        padding: '5px 11px',
        borderRadius: 7,
        cursor: 'pointer',
        border: `1px solid ${active ? 'rgba(99, 102, 241, 0.35)' : 'transparent'}`,
        background: active
          ? `linear-gradient(135deg, ${T.accentDim}, rgba(168, 85, 247, 0.08))`
          : 'transparent',
        boxShadow: active ? `0 0 18px ${T.accentGlow}, inset 0 0 12px rgba(99, 102, 241, 0.06)` : 'none',
        color: active ? '#fff' : T.textMid,
        fontSize: 12,
        fontWeight: 600,
        letterSpacing: '0.02em',
        fontFamily: "'Inter', sans-serif",
        transition: PILL_TRANSITION,
        whiteSpace: 'nowrap',
      }}
      onMouseEnter={e => {
        if (!active) {
          e.currentTarget.style.color = T.text;
          e.currentTarget.style.background = 'rgba(255, 255, 255, 0.035)';
        }
      }}
      onMouseLeave={e => {
        if (!active) {
          e.currentTarget.style.color = T.textMid;
          e.currentTarget.style.background = 'transparent';
        }
      }}
    >
      <Icon size={14} strokeWidth={active ? 2.4 : 2} />
      {meta.label}
    </button>
  );
}

export default function Header({ connected, view, onViewChange, isMobile, netWorth, cash, stockValue, totalPnl, totalPct, selectedSymbol, prices, onCommandPaletteOpen }) {
  const [clock, setClock] = useState(() => new Date().toLocaleTimeString('en-IN', { hour12: true }));
  const [showMore, setShowMore] = useState(false);
  const [showHealthModal, setShowHealthModal] = useState(false);
  const health = useHealthCheck(20000);
  const session = useMemo(() => getMarketSession(), [clock]);

  useEffect(() => {
    const timer = setInterval(() => setClock(new Date().toLocaleTimeString('en-IN', { hour12: true })), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const openHealth = () => setShowHealthModal(true);
    window.addEventListener('apex:open-health', openHealth);
    return () => window.removeEventListener('apex:open-health', openHealth);
  }, []);

  const p = prices[selectedSymbol];
  const price = p?.price ?? 0;
  const pct = p?.changePct ?? 0;
  const isUp = pct >= 0;
  const latency = health.latencyMs;
  const latencyLabel = latency == null ? '--' : latency <= 15 ? '<15ms' : `${latency}ms`;

  return (
    <div style={{
      padding: '0 16px',
      height: 56,
      display: 'flex',
      alignItems: 'center',
      gap: 14,
      borderBottom: `1px solid ${T.border}`,
      background: `linear-gradient(180deg, ${T.surface}, rgba(13, 17, 26, 0.94))`,
      backdropFilter: 'blur(14px)',
      flexShrink: 0,
      position: 'relative',
      zIndex: 40,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
        <div style={{
          width: 28,
          height: 28,
          borderRadius: 8,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: `linear-gradient(135deg, ${T.accent}, ${T.accentAlt})`,
          boxShadow: `0 0 20px ${T.accentGlow}`,
        }}>
          <Zap size={15} color="#fff" strokeWidth={2.6} />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.1 }}>
          <span style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: 13,
            fontWeight: 700,
            letterSpacing: '0.08em',
            background: `linear-gradient(135deg, #ffffff, ${T.accentAlt})`,
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            whiteSpace: 'nowrap',
          }}>
            ApexTrade
          </span>
          {!isMobile && (
            <span style={{ fontSize: 8, color: T.textDim, letterSpacing: '0.18em', fontWeight: 700 }}>
              QUANT WORKSTATION
            </span>
          )}
        </div>
      </div>

      {!isMobile && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <nav
            aria-label="Primary"
            style={{
              display: 'flex',
              background: 'rgba(7, 9, 14, 0.7)',
              borderRadius: 9,
              padding: 2,
              border: `1px solid ${T.border}`,
              flexShrink: 0,
            }}
          >
            {PRIMARY_TABS.map(tab => (
              <NavButton key={tab} tab={tab} active={view === tab} onClick={() => onViewChange(tab)} />
            ))}
          </nav>

          {SECONDARY_TABS.length > 0 && (
            <div style={{ position: 'relative' }}>
              <button
                onClick={() => setShowMore(s => !s)}
                style={{
                  padding: '6px 10px',
                  borderRadius: 7,
                  border: `1px solid ${T.border}`,
                  background: T.bg,
                  cursor: 'pointer',
                  color: SECONDARY_TABS.some(t => view === t) ? T.accentAlt : T.textDim,
                  fontSize: 10,
                  fontWeight: 700,
                  letterSpacing: '0.06em',
                  fontFamily: "'Inter', sans-serif",
                }}
              >
                MORE
              </button>
              {showMore && (
                <>
                  <div onClick={() => setShowMore(false)} style={{ position: 'fixed', inset: 0, zIndex: 99 }} />
                  <div style={{
                    position: 'absolute', top: '100%', right: 0, marginTop: 6,
                    background: T.surface, border: `1px solid ${T.borderHi}`, borderRadius: 8,
                    padding: 4, zIndex: 100, minWidth: 150, boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
                  }}>
                    {SECONDARY_TABS.map(tab => (
                      <NavButton
                        key={tab}
                        tab={tab}
                        active={view === tab}
                        onClick={() => { onViewChange(tab); setShowMore(false); }}
                      />
                    ))}
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      )}

      {!isMobile && view === 'CHART' && selectedSymbol && (
        <>
          <div style={{ width: 1, height: 24, background: T.border, flexShrink: 0 }} />
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, minWidth: 0, flexShrink: 0 }}>
            <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, fontWeight: 700, color: T.textMid, letterSpacing: '0.06em' }}>
              {selectedSymbol.replace('.NS', '')}
            </span>
            <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 17, fontWeight: 700, color: T.text, letterSpacing: '-0.02em' }}>
              ₹{fmt(price)}
            </span>
            <span style={{
              fontSize: 10,
              color: clr(pct),
              background: isUp ? T.greenDim : T.redDim,
              border: `1px solid ${isUp ? T.greenGlow : T.redGlow}`,
              padding: '1px 6px',
              borderRadius: 4,
              fontFamily: "'IBM Plex Mono', monospace",
            }}>
              {sign(pct)}{fmt(pct, 2)}%
            </span>
          </div>
        </>
      )}

      {!isMobile && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, minWidth: 0 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            <span style={{ fontSize: 8, fontWeight: 700, color: T.textDim, letterSpacing: '0.04em' }}>PORTFOLIO</span>
            <span style={{ fontSize: 12, fontWeight: 700, color: '#fff', fontFamily: "'IBM Plex Mono', monospace" }}>₹{fmt(netWorth)}</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            <span style={{ fontSize: 8, fontWeight: 700, color: T.textDim, letterSpacing: '0.04em' }}>P&amp;L</span>
            <span style={{ fontSize: 11, fontWeight: 700, color: clr(totalPnl), fontFamily: "'IBM Plex Mono', monospace" }}>
              {sign(totalPnl)}₹{fmt(Math.abs(totalPnl))} ({sign(totalPct)}{fmt(totalPct, 2)}%)
            </span>
          </div>
          <div style={{ width: 1, height: 20, background: T.border, flexShrink: 0 }} />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            <span style={{ fontSize: 8, fontWeight: 700, color: T.textDim, letterSpacing: '0.04em' }}>CASH</span>
            <span style={{ fontSize: 11, fontWeight: 700, color: T.blue, fontFamily: "'IBM Plex Mono', monospace" }}>₹{fmt(cash)}</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            <span style={{ fontSize: 8, fontWeight: 700, color: T.textDim, letterSpacing: '0.04em' }}>HOLDINGS</span>
            <span style={{ fontSize: 11, fontWeight: 700, color: T.textMid, fontFamily: "'IBM Plex Mono', monospace" }}>₹{fmt(stockValue)}</span>
          </div>
        </div>
      )}

      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 10 }}>
        {onCommandPaletteOpen && (
          <button
            onClick={onCommandPaletteOpen}
            title="Open command palette (Ctrl+K)"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 7,
              padding: '5px 9px',
              borderRadius: 7,
              border: `1px solid ${T.border}`,
              background: 'rgba(255, 255, 255, 0.02)',
              color: T.textMid,
              cursor: 'pointer',
              fontSize: 10,
              fontWeight: 600,
              letterSpacing: '0.03em',
              fontFamily: "'Inter', sans-serif",
              transition: PILL_TRANSITION,
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(99, 102, 241, 0.45)'; e.currentTarget.style.color = T.text; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = T.border; e.currentTarget.style.color = T.textMid; }}
          >
            <Search size={13} />
            {!isMobile && <span>Search</span>}
            {!isMobile && (
              <kbd style={{
                fontSize: 8,
                padding: '1px 4px',
                borderRadius: 3,
                background: T.panelAlt,
                border: `1px solid ${T.border}`,
                color: T.textDim,
                fontFamily: "'IBM Plex Mono', monospace",
              }}>
                Ctrl K
              </kbd>
            )}
          </button>
        )}

        <div
          title="Health-check round-trip latency"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 5,
            padding: '4px 7px',
            borderRadius: 6,
            border: `1px solid ${T.border}`,
            background: 'rgba(255, 255, 255, 0.02)',
            color: latency != null && latency <= 25 ? T.green : T.textMid,
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: 9,
            letterSpacing: '0.04em',
          }}
        >
          <Activity size={11} />
          {latencyLabel}
        </div>

        {!isMobile && (
          <span style={{ fontSize: 9.5, color: T.textDim, fontFamily: "'IBM Plex Mono', monospace", letterSpacing: '0.05em' }}>
            {clock} IST
          </span>
        )}

        <button
          type="button"
          onClick={() => setShowHealthModal(true)}
          title={connected ? `Quant server connected · ${session.label} · open diagnostics` : 'Quant server offline · open diagnostics'}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 7,
            padding: '4px 9px',
            borderRadius: 999,
            cursor: 'pointer',
            border: `1px solid ${!connected ? T.redGlow : session.color === T.green ? T.greenGlow : session.color === '#f5c842' ? 'rgba(245,200,66,0.3)' : T.redGlow}`,
            background: !connected ? T.redDim : session.color === T.green ? T.greenDim : session.color === '#f5c842' ? 'rgba(245,200,66,0.12)' : T.redDim,
          }}
        >
          <span style={{
            width: 6,
            height: 6,
            borderRadius: '50%',
            background: !connected ? T.red : session.color,
            boxShadow: `0 0 8px ${!connected ? T.redGlow : session.color}`,
            animation: connected && session.live ? 'pulse 2s ease-in-out infinite' : 'none',
          }} />
          <span style={{
            fontSize: 9,
            fontWeight: 700,
            color: !connected ? T.red : session.color,
            fontFamily: "'IBM Plex Mono', monospace",
            letterSpacing: '0.08em',
            whiteSpace: 'nowrap',
          }}>
            {!connected ? 'OFFLINE' : session.label}
          </span>
        </button>
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
