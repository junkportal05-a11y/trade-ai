import React, { useState, useEffect, useCallback } from 'react';
import { Settings2, BarChart3 } from 'lucide-react';
import { API_BASE_URL, apiFetch } from './api';
import { T, mono } from './theme';

const STRATEGY_PRESETS = [
  { id: 'intraday_momentum', name: 'Intraday Momentum', description: 'EMA crossover + RSI + volume filter. 15m timeframe.', riskProfile: 'Moderate', typicalHold: '15m-2h' },
  { id: 'mean_reversion', name: 'Mean Reversion', description: 'Bollinger Band squeeze + RSI extremes. 5m-15m timeframe.', riskProfile: 'Low', typicalHold: '5m-30m' },
  { id: 'breakout_volume', name: 'Breakout Volume', description: 'High volume breakout + ADX trend filter. 15m-1h timeframe.', riskProfile: 'High', typicalHold: '30m-4h' },
  { id: 'scalper_rsi', name: 'RSI Scalper', description: 'Fast RSI extremes + EMA alignment. 1m-5m timeframe.', riskProfile: 'High', typicalHold: '1m-10m' },
  { id: 'swing_trend', name: 'Swing Trend Follower', description: 'Daily EMA trend + weekly MACD. 1h-1d timeframe.', riskProfile: 'Low', typicalHold: '1d-2w' },
];

export default function StrategySelector({ selectedStrategy, onSelectStrategy, performanceData }) {
  const [strategies, setStrategies] = useState([]);
  const [dataSource, setDataSource] = useState('presets');
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('selector');

  useEffect(() => {
    // Merge presets with any backend strategies
    fetchStrategies();
  }, []);

  const fetchStrategies = useCallback(async () => {
    try {
      const res = await apiFetch('/api/strategies');
      if (res.ok) {
        const data = await res.json();
        if (data.strategies && data.strategies.length > 0) {
          setStrategies(data.strategies);
          setDataSource(data.data_source || 'presets');
          return;
        }
      }
    } catch (e) {
      // Use presets
    }
    setStrategies(STRATEGY_PRESETS);
    setDataSource('presets');
  }, []);

  const perf = performanceData || {
    total_return: 0,
    win_rate: 0,
    max_drawdown: 0,
    sharpe_ratio: 0,
    total_trades: 0,
    current_drawdown: 0,
    profit_factor: 0,
  };

  const metricCards = [
    { key: 'total_return', label: 'TOTAL RETURN', value: `${perf.total_return >= 0 ? '+' : ''}${perf.total_return.toFixed(2)}%`, color: perf.total_return >= 0 ? T.green : T.red },
    { key: 'win_rate', label: 'WIN RATE', value: `${perf.win_rate.toFixed(1)}%`, color: T.blue },
    { key: 'max_drawdown', label: 'MAX DRAWDOWN', value: `${perf.max_drawdown.toFixed(2)}%`, color: T.red },
    { key: 'sharpe_ratio', label: 'SHARPE RATIO', value: perf.sharpe_ratio.toFixed(2), color: '#f5c842' },
    { key: 'total_trades', label: 'TOTAL TRADES', value: perf.total_trades.toString(), color: T.accent },
    { key: 'profit_factor', label: 'PROFIT FACTOR', value: perf.profit_factor.toFixed(2), color: perf.profit_factor >= 1.5 ? T.green : perf.profit_factor >= 1 ? '#f5c842' : T.red },
  ];

  return (
    <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 12, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
      {/* Tab Bar */}
      <div style={{ display: 'flex', background: T.bg, borderBottom: `1px solid ${T.border}` }}>
        {[
          { id: 'selector', label: 'STRATEGIES', Icon: Settings2 },
          { id: 'performance', label: 'PERFORMANCE', Icon: BarChart3 },
        ].map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)} style={{
            flex: 1, padding: '10px 12px', border: 'none', background: 'transparent', cursor: 'pointer',
            color: activeTab === tab.id ? T.accent : T.textDim, fontSize: 9, fontWeight: 700,
            letterSpacing: '0.08em', fontFamily: "'Inter', sans-serif", borderBottom: `2px solid ${activeTab === tab.id ? T.accent : 'transparent'}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, transition: 'all 0.2s',
          }}>
            <tab.Icon size={12} /> {tab.label}
          </button>
        ))}
      </div>

      {/* Strategy Selector Tab */}
      {activeTab === 'selector' && (
        <div style={{ padding: 16, maxHeight: 400, overflowY: 'auto' }}>
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: T.textDim, letterSpacing: '0.1em', ...mono, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
              ACTIVE: {strategies.find(s => s.id === selectedStrategy)?.name || 'Intraday Momentum'}
              {dataSource === 'presets' && (
                <span style={{ fontSize: 8, letterSpacing: '0.06em', color: '#f5c842', border: '1px solid rgba(245,200,66,0.35)', borderRadius: 3, padding: '1px 5px', background: T.goldDim }}>
                  SIMULATED PRESETS
                </span>
              )}
            </div>
            <div style={{ fontSize: 11, color: T.textMid, lineHeight: 1.5 }}>
              {strategies.find(s => s.id === selectedStrategy)?.description || STRATEGY_PRESETS.find(s => s.id === selectedStrategy)?.description}
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {strategies.map(strat => {
              const isActive = selectedStrategy === strat.id;
              return (
                <button
                  key={strat.id}
                  onClick={() => onSelectStrategy?.(strat.id)}
                  style={{
                    display: 'flex', alignItems: 'flex-start', gap: 12, padding: '12px',
                    background: isActive ? T.accentDim : T.panel,
                    border: `1px solid ${isActive ? T.accent + '60' : T.border}`,
                    borderRadius: 8, cursor: 'pointer', textAlign: 'left', transition: 'all 0.2s',
                  }}
                  onMouseEnter={e => !isActive && (e.currentTarget.style.borderColor = T.accent + '40')}
                  onMouseLeave={e => !isActive && (e.currentTarget.style.borderColor = T.border)}
                >
                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: isActive ? T.accent : T.border, marginTop: 4, flexShrink: 0 }} />
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                      <span style={{ fontSize: 11, fontWeight: 700, color: isActive ? T.accentAlt : T.text, ...mono }}>{strat.name}</span>
                      {strat.riskProfile ? (
                        <span style={{ fontSize: 8, padding: '1px 6px', borderRadius: 3, background: strat.riskProfile === 'High' ? T.redDim : strat.riskProfile === 'Moderate' ? 'rgba(245,200,66,0.12)' : T.greenDim, color: strat.riskProfile === 'High' ? T.red : strat.riskProfile === 'Moderate' ? '#f5c842' : T.green, ...mono }}>
                          {strat.riskProfile}
                        </span>
                      ) : (strat.is_active != null) && (
                        <span style={{ fontSize: 8, padding: '1px 6px', borderRadius: 3, background: strat.is_active ? T.greenDim : T.redDim, color: strat.is_active ? T.green : T.red, ...mono }}>
                          {strat.is_active ? 'ACTIVE' : 'INACTIVE'}
                        </span>
                      )}
                      {strat.typicalHold && <span style={{ fontSize: 9, color: T.textDim, ...mono }}>{strat.typicalHold}</span>}
                    </div>
                    <div style={{ fontSize: 10, color: T.textMid, lineHeight: 1.4 }}>{strat.description}</div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Performance Tab */}
      {activeTab === 'performance' && (
        <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Metric Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12 }}>
            {metricCards.map(m => (
              <div key={m.key} style={{ background: T.panel, border: `1px solid ${T.border}`, borderRadius: 8, padding: '12px', textAlign: 'center' }}>
                <div style={{ fontSize: 8, fontWeight: 700, color: T.textDim, letterSpacing: '0.08em', ...mono, marginBottom: 6 }}>{m.label}</div>
                <div style={{ fontSize: 20, fontWeight: 700, color: m.color, ...mono }}>{m.value}</div>
              </div>
            ))}
          </div>

          {/* Drawdown Bar */}
          <div style={{ background: T.panel, border: `1px solid ${T.border}`, borderRadius: 8, padding: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, fontSize: 10, ...mono }}>
              <span style={{ color: T.textDim }}>CURRENT DRAWDOWN</span>
              <span style={{ color: perf.current_drawdown > 10 ? T.red : perf.current_drawdown > 5 ? '#f5c842' : T.green }}>
                {perf.current_drawdown.toFixed(2)}% / {perf.max_drawdown.toFixed(2)}% limit
              </span>
            </div>
            <div style={{ height: 8, background: T.border, borderRadius: 4, overflow: 'hidden' }}>
              <div style={{
                height: '100%',
                width: `${Math.min(100, (perf.current_drawdown / Math.max(perf.max_drawdown, 0.01)) * 100)}%`,
                background: perf.current_drawdown > perf.max_drawdown * 0.8 ? `linear-gradient(90deg, ${T.red}, ${T.red}80)` : `linear-gradient(90deg, ${T.green}, ${T.green}80)`,
                borderRadius: 4, transition: 'width 0.5s ease',
              }} />
            </div>
            {perf.current_drawdown > perf.max_drawdown && (
              <div style={{ marginTop: 8, padding: '6px 10px', background: T.redDim, border: `1px solid ${T.red}40`, borderRadius: 4, color: T.red, fontSize: 9, ...mono }}>
                ⚠ DRAWDOWN LIMIT EXCEEDED — Bot will pause new entries
              </div>
            )}
          </div>

          {/* Strategy Performance Table (if available) */}
          {perf.by_strategy && Object.keys(perf.by_strategy).length > 0 && (
            <div style={{ background: T.panel, border: `1px solid ${T.border}`, borderRadius: 8, overflow: 'hidden' }}>
              <div style={{ padding: '10px 12px', borderBottom: `1px solid ${T.border}`, fontSize: 9, fontWeight: 700, color: T.textDim, letterSpacing: '0.08em', ...mono }}>
                PERFORMANCE BY STRATEGY
              </div>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 10 }}>
                  <thead>
                    <tr style={{ color: T.textDim, borderBottom: `1px solid ${T.border}` }}>
                      <th style={{ padding: '8px 12px', textAlign: 'left' }}>STRATEGY</th>
                      <th style={{ padding: '8px 12px', textAlign: 'right' }}>TRADES</th>
                      <th style={{ padding: '8px 12px', textAlign: 'right' }}>WIN %</th>
                      <th style={{ padding: '8px 12px', textAlign: 'right' }}>RETURN</th>
                      <th style={{ padding: '8px 12px', textAlign: 'right' }}>SHARPE</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(perf.by_strategy).map(([id, s]) => (
                      <tr key={id} style={{ borderBottom: `1px solid ${T.border}` }}>
                        <td style={{ padding: '8px 12px', color: T.text, fontWeight: 700, ...mono }}>{STRATEGY_PRESETS.find(p => p.id === id)?.name || id}</td>
                        <td style={{ padding: '8px 12px', textAlign: 'right', color: T.textMid }}>{s.trades}</td>
                        <td style={{ padding: '8px 12px', textAlign: 'right', color: s.win_rate >= 50 ? T.green : T.red }}>{s.win_rate.toFixed(1)}%</td>
                        <td style={{ padding: '8px 12px', textAlign: 'right', color: s.return >= 0 ? T.green : T.red }}>{s.return >= 0 ? '+' : ''}{s.return.toFixed(2)}%</td>
                        <td style={{ padding: '8px 12px', textAlign: 'right', color: '#f5c842' }}>{s.sharpe.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}