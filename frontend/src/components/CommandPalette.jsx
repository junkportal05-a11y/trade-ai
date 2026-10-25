import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Search, X, Zap, TrendingUp, Radio, Sparkles, BarChart3, BookOpen, ShieldCheck, Bot, Home, AlertTriangle, SkipForward, Zap as ZapIcon, RotateCcw, Database, LayoutDashboard, Settings, HelpCircle, ChevronRight } from 'lucide-react';
import { T, PRIMARY_TABS, TAB_META, DEFAULT_WATCHLIST } from '../theme';

const ICON_MAP = {
  Home, Bot, TrendingUp, Radio, Sparkles, BarChart3, BookOpen, ShieldCheck,
};

const QUICK_ACTIONS = [
  { id: 'emergency-stop', label: 'Emergency Stop Bot', description: 'Immediately halt all trading activity', icon: AlertTriangle, category: 'danger' },
  { id: 'health-diag', label: 'Open Health Diagnostics', description: 'View system health, DB, broker, workers', icon: Database, category: 'system' },
  { id: 'clear-logs', label: 'Clear Order Logs', description: 'Reset trade history and order logs', icon: RotateCcw, category: 'system' },
  { id: 'refresh-analyst', label: 'Refresh AI Analyst', description: 'Force refresh AI recommendation for current symbol', icon: Sparkles, category: 'ai' },
  { id: 'scan-breakouts', label: 'Scan Breakouts', description: 'Run scanner for breakout patterns', icon: ZapIcon, category: 'ai' },
];

export default function CommandPalette({ isOpen, onClose, onViewChange, onAction, currentView, selectedSymbol, prices }) {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef(null);
  const listRef = useRef(null);

  const sections = useMemo(() => {
    const results = [];

    // Navigation views
    const navResults = PRIMARY_TABS.map(v => {
      const meta = TAB_META[v] || { icon: '', label: v };
      return {
        id: `nav-${v}`,
        label: meta.label,
        description: `Switch to ${meta.label} view`,
        icon: ICON_MAP[meta.icon] || Home,
        category: 'navigation',
        action: () => { onViewChange(v); onClose(); },
        matchText: `${meta.label} ${v}`.toLowerCase(),
      };
    });
    if (navResults.length) results.push({ title: 'Navigation', items: navResults });

    // Watchlist symbols
    const symbolResults = DEFAULT_WATCHLIST.map(w => {
      const p = prices[w.symbol];
      const price = p?.price ?? 0;
      const change = p?.changePct ?? 0;
      return {
        id: `symbol-${w.symbol}`,
        label: w.symbol.replace('.NS', ''),
        description: `${w.name} • ₹${price.toLocaleString()} (${change >= 0 ? '+' : ''}${change.toFixed(2)}%)`,
        icon: TrendingUp,
        category: 'symbols',
        action: () => { if (onAction) onAction('selectSymbol', w.symbol); onViewChange('CHART'); onClose(); },
        matchText: `${w.symbol.replace('.NS', '')} ${w.name} ${w.sector}`.toLowerCase(),
      };
    });
    if (symbolResults.length) results.push({ title: 'Symbols', items: symbolResults });

    // Quick Actions
    const actionResults = QUICK_ACTIONS.map(a => ({
      id: a.id,
      label: a.label,
      description: a.description,
      icon: a.icon,
      category: 'actions',
      action: () => { if (onAction) onAction(a.id); onClose(); },
      matchText: `${a.label} ${a.description}`.toLowerCase(),
    }));
    if (actionResults.length) results.push({ title: 'Quick Actions', items: actionResults });

    return results;
  }, [PRIMARY_TABS, DEFAULT_WATCHLIST, prices, currentView, onViewChange, onAction]);

  // Flatten all items for keyboard navigation
  const allItems = useMemo(() => sections.flatMap(s => s.items), [sections]);

  // Filter items based on query
  const filteredSections = useMemo(() => {
    if (!query.trim()) return sections;
    return sections.map(section => ({
      ...section,
      items: section.items.filter(item =>
        item.matchText.includes(query.toLowerCase()) ||
        item.label.toLowerCase().includes(query.toLowerCase()) ||
        item.description.toLowerCase().includes(query.toLowerCase())
      ),
    })).filter(s => s.items.length > 0);
  }, [query, sections]);

  const allFilteredItems = useMemo(() => filteredSections.flatMap(s => s.items), [filteredSections]);

  // Handle keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (!isOpen) return;

      if (e.key === 'Escape') {
        onClose();
        return;
      }

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex(prev => Math.min(prev + 1, allFilteredItems.length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex(prev => Math.max(prev - 1, 0));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        const item = allFilteredItems[selectedIndex];
        if (item) {
          item.action();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, allFilteredItems, selectedIndex]);

  // Focus input on open
  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const renderResults = () => {
    if (filteredSections.length === 0) {
      return (
        <div style={{ padding: '24px', textAlign: 'center', color: T.textDim }}>
          <X style={{ width: 32, height: 32, margin: '0 auto 8px', color: T.textDim }} />
          <div style={{ fontSize: 13, color: T.text }}>No matches for "{query}"</div>
          <div style={{ fontSize: 11, color: T.textDim, marginTop: 4 }}>Try a symbol name, view name, or action</div>
        </div>
      );
    }

    return (
      <>
        {filteredSections.map((section, sectionIdx) => (
          <div key={sectionIdx} style={{ padding: '8px 12px' }}>
            <div style={{ fontSize: 9, fontWeight: 700, color: T.textDim, letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 6, paddingLeft: 8 }}>
              {section.title}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {section.items.map((item, itemIdx) => {
                const flatIndex = allFilteredItems.findIndex(i => i.id === item.id);
                const isSelected = flatIndex === selectedIndex;
                const IconComponent = item.icon;

                return (
                  <button
                    key={item.id}
                    onClick={item.action}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 10,
                      width: '100%',
                      padding: '10px 12px',
                      borderRadius: 8,
                      border: 'none',
                      background: isSelected ? T.accentDim : 'transparent',
                      color: isSelected ? T.accentAlt : T.text,
                      textAlign: 'left',
                      cursor: 'pointer',
                      transition: 'all 0.1s',
                      fontFamily: "'IBM Plex Mono', monospace",
                    }}
                    onMouseEnter={() => {
                      const idx = allFilteredItems.findIndex(i => i.id === item.id);
                      if (idx !== -1) setSelectedIndex(idx);
                    }}
                  >
                    <IconComponent
                      style={{
                        width: 16, height: 16, flexShrink: 0,
                        color: isSelected ? T.accentAlt : T.textMid,
                      }}
                    />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
                        <span style={{ fontSize: 13, fontWeight: 600, color: isSelected ? T.accentAlt : T.text }}>
                          {item.label}
                        </span>
                        {item.category === 'symbols' && (
                          <span style={{ fontSize: 8, color: T.textDim, background: T.panel, padding: '1px 6px', borderRadius: 4, fontFamily: "'IBM Plex Mono', monospace" }}>
                            {item.label.toUpperCase()}
                          </span>
                        )}
                        {item.category === 'actions' && item.category === 'danger' && (
                          <span style={{ fontSize: 8, color: T.red, background: T.redDim, padding: '1px 6px', borderRadius: 4, fontFamily: "'IBM Plex Mono', monospace" }}>
                            DANGER
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: 10, color: T.textMid, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {item.description}
                      </div>
                    </div>
                    <ChevronRight style={{ width: 14, height: 14, flexShrink: 0, color: isSelected ? T.accentAlt : T.textDim, opacity: 0.5 }} />
                  </button>
                );
              })}
            </div>
          </div>
        ))}
        <div style={{ padding: '12px', borderTop: `1px solid ${T.border}`, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 16, fontSize: 10, color: T.textDim, fontFamily: "'IBM Plex Mono', monospace" }}>
          <span>↑ ↓ Navigate</span>
          <span>↵ Execute</span>
          <span>Esc Close</span>
        </div>
      </>
    );
  };

  if (!isOpen) return null;

  return (
    <div className="glass-card" style={{
      position: 'fixed',
      top: '15vh',
      left: '50%',
      transform: 'translateX(-50%)',
      width: 'min(720px, 90vw)',
      maxHeight: '70vh',
      zIndex: 9999,
      borderRadius: 16,
      padding: 8,
      boxShadow: '0 24px 48px rgba(0,0,0,0.5), 0 0 0 1px rgba(99,102,241,0.2)',
      animation: 'slideIn 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
      fontFamily: "'IBM Plex Mono', monospace",
    }}>
      {/* Search Input */}
      <div style={{ position: 'relative', padding: '8px 12px 12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Search style={{ width: 18, height: 18, color: T.textDim, flexShrink: 0 }} />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={e => { setQuery(e.target.value); setSelectedIndex(0); }}
            placeholder="Type a command, symbol, or action... (Ctrl+K to close)"
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
          <kbd style={{ fontSize: 9, color: T.textDim, padding: '2px 6px', background: T.panel, borderRadius: 4, fontFamily: "'IBM Plex Mono', monospace" }}>Esc</kbd>
        </div>
      </div>

      <div style={{ borderTop: `1px solid ${T.border}`, maxHeight: '55vh', overflowY: 'auto' }}>
        {renderResults()}
      </div>
    </div>
  );
}
