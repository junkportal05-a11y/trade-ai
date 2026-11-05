import { apiFetch } from './api';
import React, { useState, useEffect, useCallback } from 'react';
import { T } from './theme';
import { formatPercent, formatRatio, getConfidenceScore, normalizePerformanceStats } from './utils/performance';

const mono = { fontFamily: "'IBM Plex Mono', monospace" };

export default function PerformancePanel({ onViewChange }) {
  const [globalConfidence, setGlobalConfidence] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [source, setSource] = useState('loading'); // 'live' | 'simulated' | 'error'

  const fetchStats = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch(`/api/predictions/stats`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const normalized = normalizePerformanceStats(data);
      setStats(normalized.stats);
      setSource(normalized.source);
    } catch (err) {
      console.error("Error fetching performance stats:", err);
      setError(err.message);
      setStats(null);
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
        setGlobalConfidence({ ...data, confidence_score: getConfidenceScore(data) });
      }
    } catch (err) {
      console.error("Error fetching data confidence:", err);
    }
  }, []);

  useEffect(() => {
    fetchDataConfidence();
    fetchStats();
  }, [fetchDataConfidence, fetchStats]);

  const isLocked = globalConfidence?.confidence_score != null && globalConfidence.confidence_score < 90;

  const metricCards = stats ? [
    { label: "RESOLVED TRADES", value: stats.total_trades },
    { label: "WIN RATE", value: formatPercent(stats.win_rate), color: stats.win_rate == null ? T.textMid : stats.win_rate > 50 ? T.green : T.red },
    { label: "PROFIT FACTOR", value: formatRatio(stats.profit_factor), color: stats.profit_factor == null ? T.textMid : stats.profit_factor > 1.0 ? T.green : T.red },
    { label: "AVG WINNER", value: formatPercent(stats.avg_winner), color: stats.avg_winner == null ? T.textMid : T.green },
    { label: "AVG LOSER", value: formatPercent(stats.avg_loser), color: stats.avg_loser == null ? T.textMid : T.red },
    { label: "EXPECTANCY", value: formatPercent(stats.expectancy, 2), color: stats.expectancy == null ? T.textMid : stats.expectancy > 0 ? T.green : T.red },
  ] : [
    { label: "TOTAL TRADES", value: "—", action: () => onViewChange?.('PREDICTIONS'), hint: "Log a prediction to start tracking" },
    { label: "WIN RATE", value: "—", action: () => onViewChange?.('PREDICTIONS'), hint: "Resolve predictions to see win rate" },
    { label: "PROFIT FACTOR", value: "—", action: () => onViewChange?.('PREDICTIONS'), hint: "Add predictions to calculate" },
    { label: "AVG WINNER", value: "—", action: () => onViewChange?.('PREDICTIONS'), hint: "Log trades to see avg winner" },
    { label: "AVG LOSER", value: "—", action: () => onViewChange?.('PREDICTIONS'), hint: "Log trades to see avg loser" },
    { label: "EXPECTANCY", value: "—", action: () => onViewChange?.('PREDICTIONS'), hint: "Add predictions to calculate" },
  ];

  return (
    <div style={{ flex: 1, background: T.bg, padding: 24, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div style={{ borderBottom: `1px solid ${T.border}`, paddingBottom: 16 }}>
        <h2 style={{ fontSize: 22, fontWeight: 700, color: '#fff', margin: 0 }}> SYSTEM PERFORMANCE</h2>
        <p style={{ fontSize: 11, color: T.textMid, marginTop: 4 }}>Historical analytics, risk metrics, and strategy edge calculation.</p>
        {source !== 'loading' && (
          <div style={{ marginTop: 8, fontSize: 10, color: T.textMid, fontFamily: "'IBM Plex Mono', monospace" }}>
            Data source: <span style={{ color: source === 'live' ? T.green : source === 'error' ? T.red : '#fbbf24' }}>{source === 'live' ? 'RESOLVED PREDICTIONS (paper / manually resolved)' : source === 'error' ? 'UNAVAILABLE' : 'SIMULATED (no resolved predictions)'}</span>
            {stats && (
              <> · <span style={{ color: T.textMid }}>Resolved trades: {stats.total_trades} of {stats.total_predictions} predictions</span></>
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