import React, { useState, useEffect } from 'react';
import { Play, Pause, Square, ShieldCheck, Zap } from 'lucide-react';
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

  const { botData } = useBotWebSocket();

  useEffect(() => {
    setBotStatus(botData.status.state?.toLowerCase() || 'stopped');
    setLastSignal(botData.status.last_signal || null);
    setCurrentPosition(botData.status.positions?.length > 0 ? botData.status.positions[0] : null);
    setTodayPnL(botData.status.today_pnl || 0);
  }, [botData.status]);

  const handleStart = async () => {
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
      setError(e.message || 'Failed to start bot engine.');
    } finally {
      setLoading(false);
    }
  };

  const handlePause = async () => {
    setLoading(true);
    try {
      const res = await apiFetch('/api/bot/pause', { method: 'POST' });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail || 'Failed to pause bot');
      }
      setBotStatus('paused');
    } catch (e) {
      setError(e.message || 'Failed to pause bot engine.');
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    setLoading(true);
    try {
      const res = await apiFetch('/api/bot/stop', { method: 'POST' });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail || 'Failed to stop bot');
      }
      setBotStatus('stopped');
    } catch (e) {
      setError(e.message || 'Failed to stop bot engine.');
    } finally {
      setLoading(false);
    }
  };

  const isRunning = botStatus === 'running';
  const isPaused = botStatus === 'paused';

  return (
    <div className="glass-panel" style={{ borderRadius: 16, padding: 24, display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Top Header Row with Actions */}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 16 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
            <h2 style={{ fontSize: 18, fontWeight: 800, color: T.text, letterSpacing: '-0.02em', margin: 0, fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
              Bot Engine Control Matrix
            </h2>
            <span style={{
              padding: '2px 8px',
              borderRadius: 9999,
              fontSize: 10,
              fontWeight: 700,
              fontFamily: "'IBM Plex Mono', monospace",
              background: isRunning ? T.goldDim : T.redDim,
              border: `1px solid ${isRunning ? T.gold : T.red}`,
              color: isRunning ? T.gold : T.red,
            }}>
              STATUS: {botStatus.toUpperCase()}
            </span>
            <span style={{
              padding: '2px 8px',
              borderRadius: 9999,
              fontSize: 10,
              fontWeight: 700,
              background: T.goldDim,
              border: `1px solid ${T.gold}`,
              color: T.gold,
            }}>
              PAPER RUNTIME
            </span>
          </div>
          <p style={{ fontSize: 12, color: T.textMid, margin: 0, maxWidth: 600 }}>
            Autonomous signal dispatch pipeline. Simulates intraday orders on simulated NSE ticks with zero live market exposure.
          </p>
        </div>

        {/* Action Triggers: 24K Gold Start, Dark Pause, Crimson Stop */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button
            onClick={handleStart}
            disabled={loading || isRunning}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              padding: '10px 20px',
              borderRadius: 10,
              border: 'none',
              cursor: isRunning || loading ? 'not-allowed' : 'pointer',
              background: T.goldDim,
              color: T.gold,
              fontWeight: 800,
              fontSize: 12,
              letterSpacing: '0.04em',
              opacity: isRunning ? 0.6 : 1,
              transition: 'all 0.15s ease',
            }}
          >
            <Play size={14} color={T.gold} />
            <span>{loading ? 'STARTING...' : isRunning ? 'RUNNING' : 'START BOT'}</span>
          </button>

          <button
            onClick={handlePause}
            disabled={loading || !isRunning}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              padding: '10px 16px',
              borderRadius: 10,
              cursor: !isRunning || loading ? 'not-allowed' : 'pointer',
              background: isPaused ? T.orangeDim : T.bg,
              border: `1px solid ${isPaused ? T.accent : T.border}`,
              color: isPaused ? T.accent : T.textMid,
              fontWeight: 700,
              fontSize: 12,
              letterSpacing: '0.04em',
              opacity: !isRunning && !isPaused ? 0.5 : 1,
              transition: 'all 0.15s ease',
            }}
          >
            <Pause size={14} color={isPaused ? T.accent : T.textMid} />
            <span>PAUSE</span>
          </button>

          <button
            onClick={handleStop}
            disabled={loading || botStatus === 'stopped'}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              padding: '10px 18px',
              borderRadius: 10,
              border: `1px solid ${T.red}`,
              cursor: botStatus === 'stopped' || loading ? 'not-allowed' : 'pointer',
              background: T.redDim,
              color: T.red,
              fontWeight: 800,
              fontSize: 12,
              letterSpacing: '0.04em',
              opacity: botStatus === 'stopped' ? 0.5 : 1,
              transition: 'all 0.15s ease',
            }}
          >
            <Square size={12} color={T.red} />
            <span>STOP ALL</span>
          </button>
        </div>
      </div>

      {error && (
        <div style={{ padding: '10px 14px', background: T.redDim, border: `1px solid ${T.red}40`, borderRadius: 8, color: T.red, fontSize: 11, ...mono }}>
          {error}
        </div>
      )}

      {/* 4 Telemetry Tiles */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
        gap: 12,
        paddingTop: 16,
        borderTop: `1px solid ${T.border}`
      }}>
        <div style={{ padding: '14px 16px', borderRadius: 12, background: T.panel, border: `1px solid ${T.borderHi}` }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: T.textMid, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            TODAY'S P&L
          </div>
          <div style={{ fontSize: 18, fontWeight: 800, color: todayPnL >= 0 ? T.gold : T.red, marginTop: 4, fontFamily: "'IBM Plex Mono', monospace" }}>
            {todayPnL >= 0 ? '+' : ''}₹{Math.abs(todayPnL).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
        </div>

        <div style={{ padding: '14px 16px', borderRadius: 12, background: T.panel, border: `1px solid ${T.border}` }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: T.textMid, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            ACTIVE SIGNALS
          </div>
          <div style={{ fontSize: 18, fontWeight: 800, color: T.text, marginTop: 4, fontFamily: "'IBM Plex Mono', monospace" }}>
            {lastSignal ? '1' : '0'}
          </div>
        </div>

        <div style={{ padding: '14px 16px', borderRadius: 12, background: T.panel, border: `1px solid ${T.borderHi}` }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: T.textMid, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            DAILY STOP LOSS
          </div>
          <div style={{ fontSize: 18, fontWeight: 800, color: T.red, marginTop: 4, fontFamily: "'IBM Plex Mono', monospace" }}>
            ₹2,500.00
          </div>
        </div>

        <div style={{ padding: '14px 16px', borderRadius: 12, background: T.panel, border: `1px solid ${T.borderHi}` }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: T.textMid, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            SAFETY CIRCUIT
          </div>
          <div style={{ fontSize: 18, fontWeight: 800, color: T.accent, marginTop: 4, display: 'flex', alignItems: 'center', gap: 6, fontFamily: "'IBM Plex Mono', monospace" }}>
            <ShieldCheck size={18} color={T.accent} />
            <span>ARMED</span>
          </div>
        </div>
      </div>

      {/* Live Signal Telemetry */}
      {(lastSignal || currentPosition) && (
        <div style={{ borderTop: `1px solid ${T.border}`, paddingTop: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
          {lastSignal && (
            <div style={{ background: T.panel, border: `1px solid ${T.border}`, borderRadius: 10, padding: '10px 14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                <span style={{ fontSize: 9, fontWeight: 700, color: T.textMid, letterSpacing: '0.08em', ...mono }}>LAST SIGNAL</span>
                <span style={{ fontSize: 11, fontWeight: 800, color: T.gold, ...mono }}>{lastSignal.symbol?.replace('.NS', '')}</span>
              </div>
              <div style={{ display: 'flex', gap: 14, fontSize: 11, color: T.textMid, flexWrap: 'wrap' }}>
                <span><strong style={{ color: T.text }}>Signal:</strong> {lastSignal.signal}</span>
                <span><strong style={{ color: T.text }}>Conf:</strong> {lastSignal.confidence}%</span>
                <span><strong style={{ color: T.text }}>R:R:</strong> {lastSignal.rr_ratio}</span>
              </div>
            </div>
          )}
          {currentPosition && (
            <div style={{ background: T.panel, border: `1px solid ${T.border}`, borderRadius: 10, padding: '10px 14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                <span style={{ fontSize: 9, fontWeight: 700, color: T.textMid, letterSpacing: '0.08em', ...mono }}>CURRENT POSITION</span>
                <span style={{ fontSize: 11, fontWeight: 800, color: T.gold, ...mono }}>{currentPosition.symbol?.replace('.NS', '')}</span>
              </div>
              <div style={{ display: 'flex', gap: 14, fontSize: 11, color: T.textMid, flexWrap: 'wrap' }}>
                <span><strong style={{ color: T.text }}>Side:</strong> {currentPosition.side}</span>
                <span><strong style={{ color: T.text }}>Qty:</strong> {currentPosition.qty}</span>
                <span><strong style={{ color: T.text }}>Entry:</strong> ₹{currentPosition.entry_price}</span>
                <span><strong style={{ color: T.text }}>P&L:</strong> <span style={{ color: currentPosition.unrealized_pnl >= 0 ? T.gold : T.red, fontWeight: 700 }}>{currentPosition.unrealized_pnl >= 0 ? '+' : ''}₹{currentPosition.unrealized_pnl}</span></span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
