import React, { useState, useEffect } from 'react';
import { runHistoricalSimulation, getSimulationStatus, apiFetch } from './api';
import { formatError } from './utils/formatError';
import { T, mono } from './theme';

export default function SimulatorPanel({ isMobile }) {
  const [adminKey, setAdminKey] = useState(localStorage.getItem('apex_admin_key') || '');
  const [symbol, setSymbol] = useState('RELIANCE');
  const [startDate, setStartDate] = useState('2024-01-01');
  const [endDate, setEndDate] = useState('2024-12-31');
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const [isPolling, setIsPolling] = useState(false);

  useEffect(() => {
    localStorage.setItem('apex_admin_key', adminKey);
  }, [adminKey]);

  const handleStart = async () => {
    setError(null);
    setStatus(null);
    setIsPolling(true);
    try {
      // Authenticated POST via apiFetch — session cookie + token headers,
      // no hand-rolled Bearer fallback with a fake default token.
      const res = await apiFetch('/api/backtest/run', {
        method: 'POST',
        body: JSON.stringify({ symbol, start_date: startDate, end_date: endDate })
      });
      
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(formatError(data.detail || data, 'Failed to start simulation'));
      } else {
        const data = await res.json();
        if (data.error) {
          setError(formatError(data.error));
        } else {
          setStatus(data);
        }
      }
    } catch (e) {
      setError(formatError(e));
    } finally {
      setIsPolling(false);
    }
  };

  const stats = status || {};
  const winRate = stats.win_rate || 0;

  return (
    <div style={{ padding: '24px', color: T.text, background: T.bg, minHeight: '100%', overflowY: 'auto', width: '100%' }}>
      <div style={{ maxWidth: '800px', margin: '0 auto' }}>
        
        <div style={{ marginBottom: '32px' }}>
          <h1 style={{ fontSize: '24px', margin: '0 0 8px 0', color: '#fff', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '1.2em' }}>⏱</span> Historical Truth Engine
          </h1>
          <p style={{ color: T.textMuted, margin: 0, fontSize: '14px' }}>
            Time-travel simulation pipeline for backtesting trading signals at scale.
          </p>
        </div>

        {/* CONTROLS */}
        <div style={{ background: T.panel, border: `1px solid ${T.border}`, borderRadius: '12px', padding: '20px', marginBottom: '24px' }}>
          <h3 style={{ margin: '0 0 16px 0', fontSize: '16px', color: '#fff' }}>Simulation Parameters</h3>
          
          <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', marginBottom: '16px' }}>
            <div style={{ flex: '1 1 200px' }}>
              <label style={{ display: 'block', fontSize: '12px', color: T.textMuted, marginBottom: '6px' }}>Admin Key</label>
              <input 
                type="password"
                value={adminKey}
                onChange={e => setAdminKey(e.target.value)}
                placeholder="Required for execution..."
                style={{ width: '100%', padding: '10px 12px', background: T.bg, border: `1px solid ${T.border}`, color: '#fff', borderRadius: '6px', outline: 'none' }}
              />
            </div>
            <div style={{ flex: '1 1 150px' }}>
              <label style={{ display: 'block', fontSize: '12px', color: T.textMuted, marginBottom: '6px' }}>Symbol</label>
              <input 
                type="text"
                value={symbol}
                onChange={e => setSymbol(e.target.value)}
                style={{ width: '100%', padding: '10px 12px', background: T.bg, border: `1px solid ${T.border}`, color: '#fff', borderRadius: '6px', outline: 'none' }}
              />
            </div>
            <div style={{ flex: '1 1 150px' }}>
              <label style={{ display: 'block', fontSize: '12px', color: T.textMuted, marginBottom: '6px' }}>Start Date</label>
              <input 
                type="date"
                value={startDate}
                onChange={e => setStartDate(e.target.value)}
                style={{ width: '100%', padding: '10px 12px', background: T.bg, border: `1px solid ${T.border}`, color: '#fff', borderRadius: '6px', outline: 'none' }}
              />
            </div>
            <div style={{ flex: '1 1 150px' }}>
              <label style={{ display: 'block', fontSize: '12px', color: T.textMuted, marginBottom: '6px' }}>End Date</label>
              <input 
                type="date"
                value={endDate}
                onChange={e => setEndDate(e.target.value)}
                style={{ width: '100%', padding: '10px 12px', background: T.bg, border: `1px solid ${T.border}`, color: '#fff', borderRadius: '6px', outline: 'none' }}
              />
            </div>
          </div>

          {error && (
            <div style={{ padding: '12px', background: T.redDim, border: `1px solid ${T.red}`, color: T.red, borderRadius: '6px', marginBottom: '16px', fontSize: '14px' }}>
              {error}
            </div>
          )}

          <button 
            onClick={handleStart}
            disabled={isPolling || status?.is_running}
            style={{ 
              background: isPolling || status?.is_running ? T.border : T.blue, 
              color: '#fff', 
              border: 'none', 
              padding: '12px 24px', 
              borderRadius: '6px', 
              fontWeight: 600,
              cursor: isPolling || status?.is_running ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              transition: 'background 0.2s'
            }}
          >
            {isPolling || status?.is_running ? (
              <><div className="spinner" style={{ width: '16px', height: '16px', border: '2px solid #fff', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 1s linear infinite' }} /> Processing Simulation...</>
            ) : (
              ' LAUNCH SIMULATION'
            )}
          </button>
        </div>

        {/* STATUS & PROGRESS */}
        {status && (
          <div style={{ background: T.panel, border: `1px solid ${T.border}`, borderRadius: '12px', padding: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ margin: 0, fontSize: '16px', color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: status.is_running ? T.green : T.textMuted }} />
                {status.is_running ? 'Simulation Active' : 'Simulation Complete'}
              </h3>
              {status.symbol && (
                <span style={{ fontSize: '12px', padding: '4px 8px', background: 'rgba(245, 158, 11, 0.12)', color: T.accent, borderRadius: '4px', fontWeight: 600 }}>
                  Analyzing: {status.symbol}
                </span>
              )}
            </div>

            <div style={{ marginBottom: '24px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '14px', color: T.textMuted, marginBottom: '8px' }}>
                <span>Final Capital</span>
                <span style={{ color: '#fff', fontWeight: 600 }}>₹{Number(stats.final_capital || stats.capital || 10000).toLocaleString('en-IN', { maximumFractionDigits: 2 })}</span>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '16px' }}>
              
              <div style={{ background: T.bg, padding: '16px', borderRadius: '8px', border: `1px solid ${T.border}` }}>
                <div style={{ fontSize: '12px', color: T.textMuted, marginBottom: '4px' }}>Total Return</div>
                <div style={{ fontSize: '24px', color: (stats.total_pnl_pct || 0) >= 0 ? T.green : T.red, fontWeight: 600 }}>
                  {(stats.total_pnl_pct || 0) >= 0 ? '+' : ''}{stats.total_pnl_pct || 0}%
                </div>
              </div>

              <div style={{ background: T.greenDim, padding: '16px', borderRadius: '8px', border: `1px solid ${T.green}` }}>
                <div style={{ fontSize: '12px', color: T.green, marginBottom: '4px', fontWeight: 500 }}>Win Rate</div>
                <div style={{ fontSize: '24px', color: T.green, fontWeight: 600 }}>{winRate}%</div>
              </div>

              <div style={{ background: T.redDim, padding: '16px', borderRadius: '8px', border: `1px solid ${T.red}` }}>
                <div style={{ fontSize: '12px', color: T.red, marginBottom: '4px', fontWeight: 500 }}>Max Drawdown</div>
                <div style={{ fontSize: '24px', color: T.red, fontWeight: 600 }}>{stats.max_drawdown || 0}%</div>
              </div>

              <div style={{ background: T.orangeDim, padding: '16px', borderRadius: '8px', border: `1px solid ${T.orange}` }}>
                <div style={{ fontSize: '12px', color: T.orange, marginBottom: '4px', fontWeight: 500 }}>Profit Factor</div>
                <div style={{ fontSize: '24px', color: T.orange, fontWeight: 600 }}>{stats.profit_factor || '1.0'}</div>
              </div>

              <div style={{ background: T.bg, padding: '16px', borderRadius: '8px', border: `1px solid ${T.border}` }}>
                <div style={{ fontSize: '12px', color: T.textMuted, marginBottom: '4px' }}>Total Trades</div>
                <div style={{ fontSize: '24px', color: '#fff', fontWeight: 600 }}>{stats.total_trades || 0}</div>
              </div>

            </div>
          </div>
        )}

      </div>
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
