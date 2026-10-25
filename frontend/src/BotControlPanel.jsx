import React, { useState, useEffect, useCallback } from 'react';
import { Bot } from 'lucide-react';
import { API_BASE_URL, apiFetch } from './api';
import { useBotWebSocket } from './hooks/useBotWebSocket';

const T = {
  bg:         '#080a0f',
  surface:    '#0d1018',
  panel:      '#111520',
  panelAlt:   '#0f1219',
  border:     '#1a1f2e',
  borderHi:   '#252c40',
  text:       '#d0d8ed',
  textMid:    '#6e7a96',
  textDim:    '#363d55',
  green:      '#00e5a8',
  greenDim:   'rgba(0,229,168,0.1)',
  greenGlow:  'rgba(0,229,168,0.3)',
  red:        '#ff3d5a',
  redDim:     'rgba(255,61,90,0.1)',
  redGlow:    'rgba(255,61,90,0.3)',
  gold:       '#f5c842',
  goldDim:    'rgba(245,200,66,0.1)',
  blue:       '#4da6ff',
  blueDim:    'rgba(77,166,255,0.1)',
  accent:     '#7b6cff',
  accentAlt:  '#9b5de5',
  accentDim:  'rgba(123,108,255,0.12)',
};

const mono = { fontFamily: "'IBM Plex Mono', monospace" };

export default function BotControlPanel({ isPaperMode = true, onModeChange }) {
  const [botStatus, setBotStatus] = useState('stopped');
  const [lastSignal, setLastSignal] = useState(null);
  const [currentPosition, setCurrentPosition] = useState(null);
  const [todayPnL, setTodayPnL] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Personal workstation — always authenticated

  const { botData, connected } = useBotWebSocket();

  useEffect(() => {
    setBotStatus(botData.status.state?.toLowerCase() || 'stopped');
    setLastSignal(botData.status.last_signal || null);
    setCurrentPosition(botData.status.positions?.length > 0 ? botData.status.positions[0] : null);
    setTodayPnL(botData.status.today_pnl || 0);
  }, [botData.status]);

  const ensureAuth = () => true;

  const handleStart = async () => {
    if (!ensureAuth()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch('/api/bot/start', { method: 'POST', body: JSON.stringify({ paper: isPaperMode }) });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail || 'Failed to start bot');
      }
      setBotStatus('running');
    } catch (e) {
      setError(e.message || 'Authentication required. Please log in.');
    } finally {
      setLoading(false);
    }
  };

  const handlePause = async () => {
    if (!ensureAuth()) return;
    setLoading(true);
    try {
      const res = await apiFetch('/api/bot/pause', { method: 'POST' });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail || 'Failed to pause bot');
      }
      setBotStatus('paused');
    } catch (e) {
      setError(e.message || 'Authentication required. Please log in.');
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    if (!ensureAuth()) return;
    setLoading(true);
    try {
      const res = await apiFetch('/api/bot/stop', { method: 'POST' });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail || 'Failed to stop bot');
      }
      setBotStatus('stopped');
    } catch (e) {
      setError(e.message || 'Authentication required. Please log in.');
    } finally {
      setLoading(false);
    }
  };

  const statusConfig = {
    running: { color: T.green, bg: T.greenDim, glow: T.greenGlow, label: 'RUNNING', icon: '●' },
    paused:  { color: T.gold,  bg: T.goldDim,  glow: 'rgba(245,200,66,0.3)', label: 'PAUSED',  icon: '⏸' },
    stopped: { color: T.red,   bg: T.redDim,   glow: T.redGlow, label: 'STOPPED', icon: '■' },
  };

  const cfg = statusConfig[botStatus];

  return (
    <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 12, padding: 16, display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: `1px solid ${T.border}`, paddingBottom: 12 }}>


        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Bot size={18} color={T.accentAlt} />
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', color: T.accentAlt, ...mono }}>BOT ENGINE</div>
            <div style={{ fontSize: 12, fontWeight: 700, color: '#fff' }}>ApexTrade Autonomous</div>
          </div>
        </div>

        {/* Mode Toggle */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 9, color: T.textDim, ...mono }}>{isPaperMode ? 'PAPER' : 'LIVE'}</span>
          <label style={{ position: 'relative', width: 48, height: 26, cursor: 'pointer' }}>
            <input type="checkbox" checked={!isPaperMode} onChange={e => onModeChange?.(!e.target.checked)} style={{ opacity: 0, width: '100%', height: '100%', cursor: 'pointer' }} />
            <span style={{ position: 'absolute', inset: 0, background: isPaperMode ? T.border : T.red, borderRadius: 13, transition: 'background 0.2s', border: `1px solid ${isPaperMode ? T.border : T.red}` }} />
            <span style={{ position: 'absolute', top: 2, left: isPaperMode ? 2 : 24, width: 22, height: 22, background: '#fff', borderRadius: '50%', transition: 'left 0.2s', boxShadow: '0 2px 4px rgba(0,0,0,0.3)' }} />
          </label>
          <span style={{ fontSize: 9, color: T.textDim, ...mono }}>{!isPaperMode ? 'LIVE' : 'PAPER'}</span>
          {!isPaperMode && <span style={{ fontSize: 8, color: T.red, background: T.redDim, padding: '1px 4px', borderRadius: 3, ...mono }}>LOCKED</span>}
        </div>
      </div>

      {/* Status Indicator */}
      <div style={{ background: cfg.bg, border: `1px solid ${cfg.color}40`, borderRadius: 8, padding: '12px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 20, color: cfg.color, animation: 'pulse 1.5s infinite' }}>{cfg.icon}</span>
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.15em', color: cfg.color, ...mono }}>{cfg.label}</div>
            <div style={{ fontSize: 11, color: T.textMid, marginTop: 2 }}>Autonomous trading {'(' + (isPaperMode ? 'paper' : 'live') + ')'}</div>
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 10, color: T.textDim, ...mono }}>TODAY'S P&L</div>
          <div style={{ fontSize: 18, fontWeight: 700, color: todayPnL >= 0 ? T.green : T.red, ...mono }}>
            {todayPnL >= 0 ? '+' : ''}₹{Math.abs(todayPnL).toLocaleString('en-IN')}
          </div>
        </div>
      </div>



      {/* Controls */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <button onClick={handleStart} disabled={loading || botStatus === 'running'} style={{
          flex: 1, minWidth: 80, padding: '10px 16px', borderRadius: 8, border: 'none',
          background: botStatus === 'running' ? T.green : T.accent, color: '#fff',
          fontWeight: 700, fontSize: 11, letterSpacing: '0.06em', cursor: botStatus === 'running' || loading ? 'not-allowed' : 'pointer',
          fontFamily: "'IBM Plex Mono', monospace", display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
          opacity: botStatus === 'running' || loading ? 0.6 : 1,
        }}>
          {loading ? '⟳' : botStatus === 'running' ? '●' : '▶'} {botStatus === 'running' ? 'RUNNING' : 'START'}
        </button>
        <button onClick={handlePause} disabled={loading || botStatus !== 'running'} style={{
          flex: 1, minWidth: 80, padding: '10px 16px', borderRadius: 8, border: 'none',
          background: botStatus === 'paused' ? T.gold : T.goldDim, color: botStatus === 'paused' ? '#000' : T.gold,
          fontWeight: 700, fontSize: 11, letterSpacing: '0.06em', cursor: botStatus !== 'running' || loading ? 'not-allowed' : 'pointer',
          fontFamily: "'IBM Plex Mono', monospace", display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
          opacity: botStatus !== 'running' || loading ? 0.5 : 1,
        }}>
          ⏸ PAUSE
        </button>
        <button onClick={handleStop} disabled={loading || botStatus === 'stopped'} style={{
          flex: 1, minWidth: 80, padding: '10px 16px', borderRadius: 8, border: 'none',
          background: botStatus === 'stopped' ? T.red : T.redDim, color: botStatus === 'stopped' ? '#fff' : T.red,
          fontWeight: 700, fontSize: 11, letterSpacing: '0.06em', cursor: botStatus === 'stopped' || loading ? 'not-allowed' : 'pointer',
          fontFamily: "'IBM Plex Mono', monospace", display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
          opacity: botStatus === 'stopped' || loading ? 0.5 : 1,
        }}>
          ■ STOP
        </button>
      </div>

      {error && (
        <div style={{ padding: '8px 12px', background: T.redDim, border: `1px solid ${T.red}40`, borderRadius: 6, color: T.red, fontSize: 10, ...mono }}>
          {error}
        </div>
      )}

      {/* Last Signal / Position */}
      {(lastSignal || currentPosition) && (
        <div style={{ borderTop: `1px solid ${T.border}`, paddingTop: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
          {lastSignal && (
            <div style={{ background: T.panel, border: `1px solid ${T.border}`, borderRadius: 6, padding: '8px 12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ fontSize: 8, fontWeight: 700, color: T.textDim, letterSpacing: '0.08em', ...mono }}>LAST SIGNAL</span>
                <span style={{ fontSize: 10, fontWeight: 700, color: T.accent, ...mono }}>{lastSignal.symbol?.replace('.NS', '')}</span>
              </div>
              <div style={{ display: 'flex', gap: 12, fontSize: 10, color: T.textMid, flexWrap: 'wrap' }}>
                <span><strong style={{ color: T.text }}>Signal:</strong> {lastSignal.signal}</span>
                <span><strong style={{ color: T.text }}>Conf:</strong> {lastSignal.confidence}%</span>
                <span><strong style={{ color: T.text }}>R:R:</strong> {lastSignal.rr_ratio}</span>
              </div>
            </div>
          )}
          {currentPosition && (
            <div style={{ background: T.panel, border: `1px solid ${T.border}`, borderRadius: 6, padding: '8px 12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ fontSize: 8, fontWeight: 700, color: T.textDim, letterSpacing: '0.08em', ...mono }}>CURRENT POSITION</span>
                <span style={{ fontSize: 10, fontWeight: 700, color: T.blue, ...mono }}>{currentPosition.symbol?.replace('.NS', '')}</span>
              </div>
              <div style={{ display: 'flex', gap: 12, fontSize: 10, color: T.textMid, flexWrap: 'wrap' }}>
                <span><strong style={{ color: T.text }}>Side:</strong> {currentPosition.side}</span>
                <span><strong style={{ color: T.text }}>Qty:</strong> {currentPosition.qty}</span>
                <span><strong style={{ color: T.text }}>Entry:</strong> ₹{currentPosition.entry_price}</span>
                <span><strong style={{ color: T.text }}>P&L:</strong> <span style={{ color: currentPosition.unrealized_pnl >= 0 ? T.green : T.red }}>{currentPosition.unrealized_pnl >= 0 ? '+' : ''}₹{currentPosition.unrealized_pnl}</span></span>
              </div>
            </div>
          )}
        </div>
      )}

      <style>{`
        @keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.4; } }
      `}</style>
    </div>
  );
}