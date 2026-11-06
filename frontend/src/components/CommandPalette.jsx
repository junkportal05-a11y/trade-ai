import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertTriangle, BarChart3, Bot, BookOpen, ChevronRight, Database, Home, Radio,
  RotateCcw, Search, ShieldCheck, Sparkles, TrendingUp, X, Zap,
} from 'lucide-react';
import { T, PRIMARY_TABS, TAB_META, DEFAULT_WATCHLIST } from '../theme';

const ICON_MAP = { Home, Bot, TrendingUp, Radio, Sparkles, BarChart3, BookOpen, ShieldCheck };

const QUICK_ACTIONS = [
  { id: 'emergency-stop', label: 'Emergency Stop Bot', description: 'Immediately halt all trading activity', icon: AlertTriangle, danger: true },
  { id: 'health-diag', label: 'Open Health Diagnostics', description: 'View database, broker, worker, and AI status', icon: Database },
  { id: 'clear-logs', label: 'Clear Order Logs', description: 'Reset the local order and trade history view', icon: RotateCcw },
  { id: 'refresh-analyst', label: 'Refresh AI Analyst', description: 'Force a fresh recommendation for the active symbol', icon: Sparkles },
  { id: 'scan-breakouts', label: 'Scan Breakouts', description: 'Open the scanner and run a breakout sweep', icon: Zap },
];

export default function CommandPalette({ isOpen, onClose, onViewChange, onAction, selectedSymbol, prices }) {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef(null);
  const itemRefs = useRef({});

  const sections = useMemo(() => {
    const navigation = PRIMARY_TABS.map(tab => {
      const meta = TAB_META[tab] || { icon: 'Home', label: tab };
      return {
        id: `nav-${tab}`,
        label: meta.label,
        description: `Switch to ${meta.label}`,
        icon: ICON_MAP[meta.icon] || Home,
        kind: 'navigation',
        action: () => { onViewChange(tab); onClose(); },
        matchText: `${meta.label} ${tab}`.toLowerCase(),
      };
    });

    const symbols = DEFAULT_WATCHLIST.map(({ symbol, name, sector }) => {
      const quote = prices[symbol];
      const change = quote?.changePct ?? 0;
      const priceLabel = quote?.price != null ? `₹${Number(quote.price).toLocaleString('en-IN')}` : 'awaiting feed';
      return {
        id: `symbol-${symbol}`,
        label: symbol.replace('.NS', ''),
        description: `${name} · ${priceLabel} (${change >= 0 ? '+' : ''}${change.toFixed(2)}%)`,
        icon: TrendingUp,
        kind: 'symbol',
        active: symbol === selectedSymbol,
        action: () => {
          onAction?.('selectSymbol', symbol);
          onViewChange('CHART');
          onClose();
        },
        matchText: `${symbol.replace('.NS', '')} ${name} ${sector}`.toLowerCase(),
      };
    });

    const actions = QUICK_ACTIONS.map(action => ({
      id: action.id,
      label: action.label,
      description: action.description,
      icon: action.icon,
      kind: 'action',
      danger: action.danger,
      action: () => { onAction?.(action.id); onClose(); },
      matchText: `${action.label} ${action.description}`.toLowerCase(),
    }));

    return [
      { title: 'Navigation', items: navigation },
      { title: 'Symbols', items: symbols },
      { title: 'Quick Actions', items: actions },
    ].filter(section => section.items.length > 0);
  }, [onAction, onClose, onViewChange, prices, selectedSymbol]);

  const filteredSections = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return sections;
    return sections
      .map(section => ({
        ...section,
        items: section.items.filter(item =>
          item.matchText.includes(normalized) ||
          item.label.toLowerCase().includes(normalized) ||
          item.description.toLowerCase().includes(normalized)
        ),
      }))
      .filter(section => section.items.length > 0);
  }, [query, sections]);

  const flatItems = useMemo(() => filteredSections.flatMap(section => section.items), [filteredSections]);

  useEffect(() => {
    if (!isOpen) return;
    setQuery('');
    setSelectedIndex(0);
    const focusTimer = setTimeout(() => inputRef.current?.focus(), 30);
    return () => clearTimeout(focusTimer);
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const onKeyDown = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        setSelectedIndex(prev => Math.min(prev + 1, Math.max(flatItems.length - 1, 0)));
        return;
      }
      if (event.key === 'ArrowUp') {
        event.preventDefault();
        setSelectedIndex(prev => Math.max(prev - 1, 0));
        return;
      }
      if (event.key === 'Enter') {
        event.preventDefault();
        flatItems[selectedIndex]?.action();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [flatItems, isOpen, onClose, selectedIndex]);

  useEffect(() => {
    const item = flatItems[selectedIndex];
    if (item) itemRefs.current[item.id]?.scrollIntoView({ block: 'nearest' });
  }, [flatItems, selectedIndex]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  if (!isOpen) return null;

  const renderResults = () => {
    if (!flatItems.length) {
      return (
        <div style={{ padding: 32, textAlign: 'center', color: T.textDim }}>
          <Search size={28} style={{ margin: '0 auto 10px', opacity: 0.4 }} />
          <div style={{ fontSize: 13, color: T.text }}>No matches for “{query}”</div>
          <div style={{ fontSize: 11, color: T.textDim, marginTop: 4 }}>Try a symbol, view name, or quick action.</div>
        </div>
      );
    }

    return filteredSections.map(section => (
      <div key={section.title} style={{ padding: '8px 10px 2px' }}>
        <div style={{ fontSize: 9, fontWeight: 700, color: T.textDim, letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 5, paddingLeft: 9 }}>
          {section.title}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {section.items.map(item => {
            const flatIndex = flatItems.findIndex(candidate => candidate.id === item.id);
            const isSelected = flatIndex === selectedIndex;
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                ref={node => { itemRefs.current[item.id] = node; }}
                onClick={item.action}
                onMouseEnter={() => setSelectedIndex(flatIndex)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  width: '100%',
                  padding: '9px 10px',
                  borderRadius: 8,
                  border: `1px solid ${isSelected ? T.borderHi : 'transparent'}`,
                  background: isSelected
                    ? `linear-gradient(135deg, ${T.accentDim}, ${T.goldDim})`
                    : 'transparent',
                  boxShadow: isSelected ? `0 0 18px ${T.accentGlow}` : 'none',
                  color: isSelected ? T.text : T.text,
                  textAlign: 'left',
                  cursor: 'pointer',
                  transition: 'all 0.12s ease',
                  fontFamily: "'IBM Plex Mono', monospace",
                }}
              >
                <Icon size={16} style={{ flexShrink: 0, color: isSelected ? T.accentAlt : T.textMid }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 2 }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: isSelected ? '#fff' : T.text }}>
                      {item.label}
                    </span>
                    {item.active && (
                      <span style={{ fontSize: 8, color: T.green, background: T.greenDim, border: `1px solid ${T.greenGlow}`, padding: '1px 5px', borderRadius: 4 }}>
                        ACTIVE
                      </span>
                    )}
                    {item.danger && (
                      <span style={{ fontSize: 8, color: T.red, background: T.redDim, border: `1px solid ${T.redGlow}`, padding: '1px 5px', borderRadius: 4 }}>
                        DANGER
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: 10, color: T.textMid, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {item.description}
                  </div>
                </div>
                <ChevronRight size={14} style={{ flexShrink: 0, color: isSelected ? T.accentAlt : T.textDim, opacity: 0.6 }} />
              </button>
            );
          })}
        </div>
      </div>
    ));
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Command palette"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 9998,
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'center',
        paddingTop: '14vh',
        background: 'rgba(0, 0, 0, 0.68)',
        backdropFilter: 'blur(6px)',
        WebkitBackdropFilter: 'blur(6px)',
        animation: 'fadeIn 0.15s ease',
      }}
      onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}
    >
      <div
        className="glass-card"
        style={{
          width: 'min(720px, 92vw)',
          maxHeight: '72vh',
          display: 'flex',
          flexDirection: 'column',
          borderRadius: 16,
          overflow: 'hidden',
          boxShadow: '0 28px 60px rgba(0, 0, 0, 0.75), 0 0 0 1px ${T.borderHi}, 0 0 40px ${T.goldDim}',
          animation: 'slideIn 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
          fontFamily: "'IBM Plex Mono', monospace",
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '14px 16px', borderBottom: `1px solid ${T.border}` }}>
          <Search size={18} color={T.textDim} style={{ flexShrink: 0 }} />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={event => setQuery(event.target.value)}
            placeholder="Search symbols, views, or actions..."
            aria-label="Search commands"
            style={{
              flex: 1,
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: T.text,
              fontSize: 15,
              fontFamily: "'IBM Plex Mono', monospace",
              letterSpacing: '0.02em',
            }}
          />
          <button
            onClick={onClose}
            aria-label="Close command palette"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              background: T.panel,
              border: `1px solid ${T.border}`,
              color: T.textDim,
              borderRadius: 5,
              padding: '2px 6px',
              cursor: 'pointer',
              fontSize: 9,
              fontFamily: "'IBM Plex Mono', monospace",
            }}
          >
            <X size={10} />
            ESC
          </button>
        </div>

        <div style={{ overflowY: 'auto', paddingBottom: 6 }}>
          {renderResults()}
        </div>

        <div style={{
          padding: '10px 14px',
          borderTop: `1px solid ${T.border}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 16,
          fontSize: 9,
          color: T.textDim,
          fontFamily: "'IBM Plex Mono', monospace",
        }}>
          <span>↑ ↓ Navigate</span>
          <span>↵ Execute</span>
          <span>Esc Close</span>
        </div>
      </div>
    </div>
  );
}
