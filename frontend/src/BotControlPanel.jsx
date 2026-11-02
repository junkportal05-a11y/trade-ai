import React, { useState, useEffect, useCallback } from 'react';
import { Bot } from 'lucide-react';
import { apiFetch } from './api';
import { useBotWebSocket } from './hooks/useBotWebSocket';
import { buildBotStartPayload } from './utils/botMode';
import { T, mono } from './theme';

export default function BotControlPanel() {
  const [botStatus, setBotStatus] = useState('stopped');
  const [lastSignal, setLastSignal] = useState(null);
  const [currentPosition, setCurrentPosition] = useState(null);
  const [todayPnL, setTodayPnL] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Personal workstation — always authenticated

  const { botData } = useBotWebSocket();

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
      const res = await apiFetch('/api/bot/start', { method: 'POST', body: JSON.stringify(buildBotStartPayload()) });
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
    paused:  { color: '#f5c842',  bg: 'rgba(245,200,66,0.12)',  glow: 'rgba(245,200,66,0.3)', label: 'PAUSED',  icon: '⏸' },
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

        {/* Paper-only: live trading is not exposed in this workstation build. */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 9, fontWeight: 700, color: T.green, background: T.greenDim, border: `1px solid ${T.greenGlow}`, padding: '2px 7px', borderRadius: 4, ...mono }}>PAPER ONLY</span>
        </div>
      </div>

      {/* Status Indicator */}
      <div style={{ background: cfg.bg, border: `1px solid ${cfg.color}40`, borderRadius: 8, padding: '12px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 20, color: cfg.color, animation: 'pulse 1.5s infinite' }}>{cfg.icon}</span>
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.15em', color: cfg.color, ...mono }}>{cfg.label}</div>
            <div style={{ fontSize: 11, color: T.textMid, marginTop: 2 }}>Autonomous trading (paper)</div>
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
          background: botStatus === 'paused' ? '#f5c842' : 'rgba(245,200,66,0.12)', color: botStatus === 'paused' ? '#000' : '#f5c842',
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