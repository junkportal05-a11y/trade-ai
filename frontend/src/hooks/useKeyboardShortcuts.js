import { useEffect, useCallback } from 'react';

/**
 * Global keyboard shortcuts for trading operations
 * B - Buy, S - Sell, 1-6 - Timeframes, Tab - Cycle symbols
 */
export function useKeyboardShortcuts({
  onBuy,
  onSell,
  onTimeframeChange,
  onCycleSymbol,
  onFocusSearch,
  onToggleBot,
  onToggleChart,
  enabled = true,
}) {
  const handleKeyDown = useCallback((event) => {
    // Don't trigger shortcuts when typing in inputs
    const target = event.target;
    const isInput = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable;
    if (isInput && !event.metaKey && !event.ctrlKey) return;

    // Don't trigger if modal is open (check for common modal classes)
    if (document.querySelector('[role="dialog"], .fixed.inset-0')) return;

    const key = event.key.toLowerCase();

    switch (key) {
      case 'b':
        if (onBuy) {
          event.preventDefault();
          onBuy();
        }
        break;
      case 's':
        if (onSell) {
          event.preventDefault();
          onSell();
        }
        break;
      case '1':
      case '2':
      case '3':
      case '4':
      case '5':
      case '6':
        if (onTimeframeChange) {
          event.preventDefault();
          const timeframes = ['1m', '5m', '15m', '1h', '1d', '1w'];
          onTimeframeChange(timeframes[parseInt(key, 10) - 1]);
        }
        break;
      case 'tab':
        if (onCycleSymbol) {
          event.preventDefault();
          onCycleSymbol(event.shiftKey); // Shift+Tab = previous
        }
        break;
      case '/':
        if (onFocusSearch) {
          event.preventDefault();
          onFocusSearch();
        }
        break;
      case ' ':
        if (onToggleBot) {
          event.preventDefault();
          onToggleBot();
        }
        break;
      case 'c':
        if (onToggleChart) {
          event.preventDefault();
          onToggleChart();
        }
        break;
      default:
        break;
    }
  }, [onBuy, onSell, onTimeframeChange, onCycleSymbol, onFocusSearch, onToggleBot, onToggleChart]);

  useEffect(() => {
    if (!enabled) return;
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown, enabled]);
}

/**
 * Cheatsheet for displaying available shortcuts
 */
export const KEYBOARD_SHORTCUTS = [
  { key: 'B', description: 'Buy / Long' },
  { key: 'S', description: 'Sell / Short' },
  { key: '1-6', description: 'Timeframes (1m, 5m, 15m, 1h, 1d, 1w)' },
  { key: 'Tab', description: 'Cycle symbol forward' },
  { key: 'Shift+Tab', description: 'Cycle symbol backward' },
  { key: '/', description: 'Focus search / command palette' },
  { key: 'Space', description: 'Toggle bot start/pause' },
  { key: 'C', description: 'Toggle chart panel' },
];

export default useKeyboardShortcuts;