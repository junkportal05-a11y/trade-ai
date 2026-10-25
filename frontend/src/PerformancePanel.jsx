import { API_BASE_URL, apiFetch } from './api';
import React, { useState, useEffect, useCallback } from 'react';

export default function PerformancePanel() {
  const [globalConfidence, setGlobalConfidence] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [source, setSource] = useState('loading'); // 'live' | 'simulated' | 'error'

  const fetchStats = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Try to get stats from predictions/stats endpoint
      const res = await apiFetch(`/api/predictions/stats`);
      if (res.ok) {
        const data = await res.json();
        if (data.resolved_predictions > 0) {
          setStats({
            total_trades: data.total_predictions,
            win_rate: data.win_rate,
            profit_factor: data.profit_factor,
            avg_winner: data.avg_win || 0,
            avg_loser: data.avg_loss || 0,
            expectancy: data.expected_value_pct || 0,
          });
          setSource('live');
        } else {
          // No resolved predictions yet - use bot stats if available
          const botRes = await apiFetch('/api/bot/status');
          if (botRes.ok) {
            const botData = await botRes.json();
            setStats({
              total_trades: botData.trades?.length || 0,
              win_rate: 0,
              profit_factor: 0,
              avg_winner: 0,
              avg_loser: 0,
              expectancy: 0,
            });
            setSource('simulated');
          } else {
            setStats({
              total_trades: 0,
              win_rate: 0,
              profit_factor: 0,
              avg_winner: 0,
              avg_loser: 0,
              expectancy: 0,
            });
            setSource('simulated');
          }
        }
      } else {
        throw new Error(`HTTP ${res.status}`);
      }
    } catch (err) {
      console.error("Error fetching performance stats:", err);
      setError(err.message);
      setStats({
        total_trades: 0,
        win_rate: 0,
        profit_factor: 0,
        avg_winner: 0,
        avg_loser: 0,
        expectancy: 0,
      });
      setSource('error');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchDataConfidence = useCallback(async () => {
    try {
      const res = await apiFetch(`/api/data/confidence`);
      if (res.ok) {
        const data = await res.json();
        setGlobalConfidence({ ...data, confidence_score: data.overall_confidence ?? data.confidence_score ?? 92 });
      }
    } catch (err) {
      console.error("Error fetching data confidence:", err);
    }
  }, []);

  useEffect(() => {
    fetchDataConfidence();
    fetchStats();
  }, [fetchDataConfidence, fetchStats]);

  const isLocked = globalConfidence?.confidence_score !== undefined && globalConfidence.confidence_score < 90;

  const metricCards = stats ? [
    { label: "TOTAL TRADES", value: stats.total_trades },
    { label: "WIN RATE", value: `${stats.win_rate}%`, color: stats.win_rate > 50 ? T.green : T.red },
    { label: "PROFIT FACTOR", value: stats.profit_factor?.toFixed?.(2) ?? stats.profit_factor, color: stats.profit_factor > 1.0 ? T.green : T.red },
    { label: "AVG WINNER", value: `${stats.avg_winner}%`, color: T.green },
    { label: "AVG LOSER", value: `${stats.avg_loser}%`, color: T.red },
    { label: "EXPECTANCY", value: `${stats.expectancy}%`, color: stats.expectancy > 0 ? T.green : T.red },
  ] : [
    { label: "TOTAL TRADES", value: "—", action: () => setView('PREDICTIONS'), label: "Log a prediction to start tracking" },
    { label: "WIN RATE", value: "—", action: () => setView('PREDICTIONS'), label: "Resolve predictions to see win rate" },
    { label: "PROFIT FACTOR", value: "—", action: () => setView('PREDICTIONS'), label: "Add predictions to calculate" },
    { label: "AVG WINNER", value: "—", action: () => setView('PREDICTIONS'), label: "Log trades to see avg winner" },
    { label: "AVG LOSER", value: "—", action: () => setView('PREDICTIONS'), label: "Log trades to see avg loser" },
    { label: "EXPECTANCY", value: "—", action: () => setView('PREDICTIONS'), label: "Add predictions to calculate" },
  ];

  return (
    <div style={{ flex: 1, background: T.bg, padding: 24, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div style={{ borderBottom: `1px solid ${T.border}`, paddingBottom: 16 }}>
        <h2 style={{ fontSize: 22, fontWeight: 700, color: '#fff', margin: 0 }}> SYSTEM PERFORMANCE</h2>
        <p style={{ fontSize: 11, color: T.textMid, marginTop: 4 }}>Historical analytics, risk metrics, and strategy edge calculation.</p>
        {source !== 'loading' && (
          <div style={{ marginTop: 8, fontSize: 10, color: T.textMid, fontFamily: "'IBM Plex Mono', monospace" }}>
            Data source: <span style={{ color: source === 'live' ? T.green : source === 'error' ? T.red : T.gold }}>{source === 'live' ? 'LIVE (predictions resolved)' : source === 'error' ? 'UNAVAILABLE' : 'SIMULATED (no resolved predictions)'}</span>
            {stats && stats.total_trades !== undefined && (
              <> · <span style={{ color: T.textMid }}>Total trades: {stats.total_trades}</span></>
            )}
          </div>
        )}
      </div>

      {isLocked && (
        <div style={{ background: T.redDim, border: `1px solid ${T.red}`, padding: 12, borderRadius: 8, display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>⚠</span>
          <div>
            <div style={{ color: T.red, fontWeight: 700, fontSize: 12, letterSpacing: '0.04em' }}>DATA INTEGRITY COMPROMISED</div>
            <div style={{ color: T.text, fontSize: 11, opacity: 0.9 }}>
              Database Data Confidence Score is {(globalConfidence.confidence_score ?? 0).toFixed(1)}% (Below 90% threshold). Analytics have been locked to prevent decision making on corrupted historical data.
            </div>
          </div>
        </div>
      )}

      {/* Analytics container with Blur logic */}
      <div style={{ 
        display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16,
        filter: isLocked ? 'blur(6px)' : 'none', 
        pointerEvents: isLocked ? 'none' : 'auto', 
        transition: 'all 0.3s ease',
        userSelect: isLocked ? 'none' : 'auto'
      }}>
        {/* Metric cards */}
        {metricCards.map((m, i) => (
          <div key={i} style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 10, padding: 16, display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: T.textMid, letterSpacing: '0.05em', marginBottom: 8 }}>{m.label}</div>
            <div style={{ fontSize: 24, fontWeight: 300, color: m.color || '#fff', ...mono }}>{m.value}</div>
            {m.action && (
              <button
                onClick={m.action}
                style={{
                  marginTop: 8,
                  padding: '6px 12px',
                  background: 'transparent',
                  border: `1px solid ${T.borderHi}`,
                  borderRadius: 6,
                  color: T.accent,
                  fontSize: 10,
                  fontWeight: 600,
                  cursor: 'pointer',
                  fontFamily: "'Inter', sans-serif",
                  transition: 'all 0.15s',
                }}
                onMouseEnter={e => { e.currentTarget.style.background = T.accentDim; e.currentTarget.style.borderColor = T.accent; }}
                onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.borderColor = T.borderHi; }}
              >
                {m.label}
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}