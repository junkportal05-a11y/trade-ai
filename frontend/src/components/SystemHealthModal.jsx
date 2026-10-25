import React, { useEffect, useState } from 'react';
import { T, clr } from '../theme';

export default function SystemHealthModal({ isOpen, onClose, health, onRefresh }) {
  const [expanded, setExpanded] = useState({});

  if (!isOpen) return null;

  const getStatusColor = (status) => {
    if (!status) return T.textDim;
    const s = status.toLowerCase();
    if (s === 'healthy' || s === 'open' || s === 'configured') return T.green;
    if (s === 'degraded' || s === 'warning' || s === 'not_configured') return '#f5c842';
    if (s === 'unhealthy' || s === 'error' || s === 'closed') return T.red;
    return T.textMid;
  };

  const getStatusIcon = (status) => {
    if (!status) return '?';
    const s = status.toLowerCase();
    if (s === 'healthy' || s === 'open' || s === 'configured') return '✓';
    if (s === 'degraded' || s === 'warning' || s === 'not_configured') return '!';
    if (s === 'unhealthy' || s === 'error' || s === 'closed') return '✗';
    return '?';
  };

  const formatLatency = (ms) => {
    if (ms === null || ms === undefined) return 'N/A';
    return ms < 1000 ? `${Math.round(ms)}ms` : `${(ms / 1000).toFixed(2)}s`;
  };

  const renderCheck = (key, check, depth = 0) => {
    if (!check) return null;
    const indent = depth * 16;
    const isExpandable = typeof check === 'object' && check !== null && !Array.isArray(check) && Object.keys(check).length > 0;
    
    const status = check.status || (check.healthy !== undefined ? (check.healthy ? 'healthy' : 'unhealthy') : 'unknown');
    const color = getStatusColor(status);
    const icon = getStatusIcon(status);

    if (isExpandable) {
      const isExp = expanded[key] || false;
      return (
        <div key={key} style={{ marginLeft: indent }}>
          <button
            onClick={() => setExpanded({ ...expanded, [key]: !isExp })}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              background: 'none',
              border: 'none',
              color: T.text,
              cursor: 'pointer',
              padding: '4px 0',
              fontSize: 11,
              fontFamily: "'Inter', sans-serif",
              textAlign: 'left',
              width: '100%',
            }}
          >
            <span style={{ fontFamily: "'IBM Plex Mono', monospace", color: T.textDim }}>▸</span>
            <span style={{ color, fontFamily: "'IBM Plex Mono', monospace", fontSize: 10 }}>{icon}</span>
            <span style={{ color, fontWeight: 600, textTransform: 'capitalize' }}>{key.replace(/_/g, ' ')}</span>
            <span style={{ marginLeft: 'auto', color: T.textDim, fontSize: 9 }}>{isExp ? '▼' : '▶'}</span>
          </button>
          {isExp && (
            <div style={{ marginTop: 4 }}>
              {Object.entries(check).map(([subKey, subVal]) => (
                renderCheck(subKey, subVal, depth + 1)
              ))}
            </div>
          )}
        </div>
      );
    }

    // Leaf node
    let displayValue = '';
    if (typeof check === 'object' && check !== null) {
      const parts = [];
      if (check.latency_ms !== undefined) parts.push(`Latency: ${formatLatency(check.latency_ms)}`);
      if (check.mode) parts.push(`Mode: ${check.mode.toUpperCase()}`);
      if (check.live_armed !== undefined) parts.push(check.live_armed ? 'ARMED' : 'Paper');
      if (check.type) parts.push(`Type: ${check.type}`);
      if (check.message) parts.push(check.message);
      if (check.error) parts.push(`Error: ${check.error}`);
      if (check.configured !== undefined) parts.push(check.configured ? 'Configured' : 'Not Configured');
      if (check.exists !== undefined) parts.push(check.exists ? 'Found' : 'Missing');
      if (check.free_gb !== undefined) parts.push(`Free: ${check.free_gb} GB (${check.usage_pct}% used)`);
      if (check.is_open !== undefined) parts.push(check.is_open ? 'OPEN' : 'CLOSED');
      if (check.workers) {
        const w = check.workers;
        Object.entries(w).forEach(([wName, wStatus]) => {
          const ws = typeof wStatus === 'object' ? wStatus.status : wStatus;
          parts.push(`${wName}: ${ws}`);
        });
      }
      displayValue = parts.join(' | ');
    } else {
      displayValue = String(check);
    }

    return (
      <div key={key} style={{ marginLeft: indent, padding: '4px 0', display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ color, fontFamily: "'IBM Plex Mono', monospace", fontSize: 10 }}>{icon}</span>
        <span style={{ color: T.textMid, fontSize: 11, minWidth: 140, textTransform: 'capitalize' }}>{key.replace(/_/g, ' ')}</span>
        <span style={{ color: T.text, fontSize: 11, fontFamily: "'Inter', sans-serif", flex: 1 }}>{displayValue}</span>
      </div>
    );
  };

  const checks = health?.checks || {};
  const overallStatus = health?.status || 'checking';
  const latency = health?.latencyMs;
  const lastChecked = health?.lastChecked;
  const version = health?.version;
  const environment = health?.environment;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.7)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        animation: 'fadeIn 0.2s ease-out',
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: T.surface,
          border: `1px solid ${T.border}`,
          borderRadius: 12,
          padding: 24,
          maxWidth: 640,
          width: '90%',
          maxHeight: '85vh',
          overflow: 'auto',
          boxShadow: '0 24px 48px rgba(0,0,0,0.6)',
          animation: 'slideUp 0.25s ease-out',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{
              width: 10, height: 10, borderRadius: '50%',
              background: getStatusColor(overallStatus),
              boxShadow: overallStatus === 'healthy' ? `0 0 12px ${getStatusColor(overallStatus)}` : 'none',
            }} />
            <span style={{ fontSize: 16, fontWeight: 700, fontFamily: "'IBM Plex Mono', monospace", letterSpacing: '0.06em' }}>
              SYSTEM HEALTH
            </span>
            <span style={{
              fontSize: 10,
              fontWeight: 700,
              padding: '2px 8px',
              borderRadius: 4,
              background: `${getStatusColor(overallStatus)}20`,
              color: getStatusColor(overallStatus),
              border: `1px solid ${getStatusColor(overallStatus)}`,
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
            }}>
              {overallStatus.toUpperCase()}
            </span>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: T.textDim,
              fontSize: 20,
              cursor: 'pointer',
              padding: 4,
              lineHeight: 1,
            }}
          >
            ✕
          </button>
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginBottom: 16, fontSize: 10, color: T.textDim }}>
          <span style={{ fontFamily: "'IBM Plex Mono', monospace" }}>v{version || '?'}</span>
          <span>•</span>
          <span style={{ fontFamily: "'IBM Plex Mono', monospace", textTransform: 'capitalize' }}>{environment || 'development'}</span>
          <span>•</span>
          <span>Latency: {formatLatency(latency)}</span>
          <span>•</span>
          <span>Updated: {lastChecked ? new Date(lastChecked).toLocaleTimeString() : '—'}</span>
        </div>

        <div style={{ borderTop: `1px solid ${T.border}`, paddingTop: 16 }}>
          {Object.entries(checks).map(([key, check]) => renderCheck(key, check))}
        </div>

        <div style={{ marginTop: 20, paddingTop: 16, borderTop: `1px solid ${T.border}`, display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
          <button
            onClick={onClose}
            style={{
              padding: '8px 16px',
              borderRadius: 6,
              border: `1px solid ${T.border}`,
              background: T.bg,
              color: T.text,
              fontSize: 10,
              fontWeight: 600,
              fontFamily: "'Inter', sans-serif",
              cursor: 'pointer',
            }}
          >
            Close
          </button>
          <button
            onClick={onRefresh}
            style={{
              padding: '8px 16px',
              borderRadius: 6,
              border: 'none',
              background: T.accent,
              color: T.accentAlt,
              fontSize: 10,
              fontWeight: 600,
              fontFamily: "'Inter', sans-serif",
              cursor: 'pointer',
            }}
          >
            Refresh Now
          </button>
        </div>
      </div>

      <style jsx>{`
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes slideUp { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: translateY(0); } }
      `}</style>
    </div>
  );
}