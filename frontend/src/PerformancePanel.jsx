import { API_BASE_URL, apiFetch } from './api';
import React, { useState, useEffect, useCallback } from 'react';

const T = {
  bg:       '#080a0f',
  surface:  '#0d1018',
  panel:    '#111520',
  border:   '#1a1f2e',
  borderHi: '#252c40',
  text:     '#d0d8ed',
  textMid:  '#6e7a96',
  textDim:  '#363d55',
  green:    '#00e5a8',
  red:      '#ff3d5a',
  redDim:   'rgba(255,61,90,0.1)',
  blue:     '#4da6ff',
  gold:     '#f5c842',
  accent:   '#7b6cff',
};

const mono = { fontFamily: "'IBM Plex Mono', monospace" };

export default function PerformancePanel() {
  const [globalConfidence, setGlobalConfidence] = useState(null);
  const [stats, setStats] = useState({
    total_trades: 124,
    win_rate: 68.5,
    profit_factor: 1.45,
    avg_winner: 12.4,
    avg_loser: -8.2,
    expectancy: 3.1
  });

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
  }, [fetchDataConfidence]);

  const isLocked = globalConfidence?.locked;

  return (
    <div style={{ flex: 1, background: T.bg, padding: 24, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div style={{ borderBottom: `1px solid ${T.border}`, paddingBottom: 16 }}>
        <h2 style={{ fontSize: 22, fontWeight: 700, color: '#fff', margin: 0 }}> SYSTEM PERFORMANCE</h2>
        <p style={{ fontSize: 11, color: T.textMid, marginTop: 4 }}>Historical analytics, risk metrics, and strategy edge calculation.</p>
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
        {[
          { label: "TOTAL TRADES", value: stats.total_trades },
          { label: "WIN RATE", value: `${stats.win_rate}%`, color: stats.win_rate > 50 ? T.green : T.red },
          { label: "PROFIT FACTOR", value: stats.profit_factor, color: stats.profit_factor > 1.0 ? T.green : T.red },
          { label: "AVG WINNER", value: `${stats.avg_winner}%`, color: T.green },
          { label: "AVG LOSER", value: `${stats.avg_loser}%`, color: T.red },
          { label: "EXPECTANCY", value: `${stats.expectancy}%`, color: stats.expectancy > 0 ? T.green : T.red },
        ].map((m, i) => (
          <div key={i} style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 10, padding: 16 }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: T.textMid, letterSpacing: '0.05em', marginBottom: 8 }}>{m.label}</div>
            <div style={{ fontSize: 24, fontWeight: 300, color: m.color || '#fff', ...mono }}>{m.value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
