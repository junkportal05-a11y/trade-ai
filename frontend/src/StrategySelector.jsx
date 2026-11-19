import React, { useState, useEffect, useCallback } from 'react';
import { Settings2, BarChart3, ShieldCheck, Zap, Brain, TrendingUp, BarChart, TrendingDown, Loader2 } from 'lucide-react';
import { apiFetch } from './api';
import { T, mono } from './theme';

const STRATEGY_PRESETS = [
  { 
    id: 'trend_scalper', 
    name: 'Trend Scalper', 
    icon: TrendingUp,
    type: 'Momentum Breakout', 
    description: 'Volume breakouts in top 20 liquid NSE contracts with dynamic ATR trailing stops. Fast entries, quick exits.',
    risk: 'Moderate', 
    winRate: '54.0%', 
    enabled: true 
  },
  { 
    id: 'mean_reversion', 
    name: 'Mean Reversion', 
    icon: TrendingDown,
    type: 'Statistical Arb', 
    description: 'Fades overextended 2-SD moves at Bollinger extremes during midday consolidation. High win rate, smaller moves.',
    risk: 'Low', 
    winRate: '58.5%', 
    enabled: true 
  },
  { 
    id: 'breakout_volume', 
    name: 'Breakout Volume', 
    icon: BarChart,
    type: 'Directional', 
    description: 'Trades opening range breakouts (ORB 15-min) with 2.5x standard relative volume. Momentum follow-through.',
    risk: 'High', 
    winRate: '49.8%', 
    enabled: false 
  },
  { 
    id: 'rsi_scalper', 
    name: 'RSI Scalper', 
    icon: Zap,
    type: 'Micro Scalp', 
    description: 'Fast 5-min momentum exhaustion targeting 0.35% quick scalp moves with strict exit. High frequency.',
    risk: 'Moderate', 
    winRate: '52.1%', 
    enabled: false 
  },
  { 
    id: 'swing_trend_follower', 
    name: 'Swing Trend Follower', 
    icon: Brain,
    type: 'Trend Horizon', 
    description: 'Filters 15m and 60m trend alignment using SuperTrend dual-engine logic. Longer hold, trend capture.',
    risk: 'Low', 
    winRate: '51.2%', 
    enabled: true 
  },
];

const ICON_COLORS = {
  trend_scalper: T.green,
  mean_reversion: T.accent,
  breakout_volume: T.gold,
  rsi_scalper: '#ff6b35',
  swing_trend_follower: T.blue,
};

export default function StrategySelector({ selectedStrategy, onSelectStrategy, performanceData }) {
  const [strategies, setStrategies] = useState(STRATEGY_PRESETS);
  const [activeTab, setActiveTab] = useState('engines'); // 'engines' | 'backtest' | 'accuracy'
  const [backtestResults, setBacktestResults] = useState(null);
  const [accuracyData, setAccuracyData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchStrategies();
    fetchAccuracyComparison();
  }, []);

  const fetchStrategies = useCallback(async () => {
    try {
      const res = await apiFetch('/api/strategies');
      if (res.ok) {
        const data = await res.json();
        if (data.strategies && data.strategies.length > 0) {
          const merged = data.strategies.map((s, idx) => {
            const preset = STRATEGY_PRESETS.find(p => p.id === s.id) || STRATEGY_PRESETS[idx % STRATEGY_PRESETS.length];
            return {
              ...preset,
              ...s,
              enabled: s.is_active ?? true,
            };
          });
          setStrategies(merged);
        }
      }
    } catch {
      // Use defaults
    }
  }, []);

  const fetchAccuracyComparison = useCallback(async () => {
    try {
      const res = await apiFetch('/api/predictions/stats');
      if (res.ok) {
        const data = await res.json();
        setAccuracyData(data);
      }
    } catch {
      // Use empty state
    }
  }, []);

  const handleBacktestRun = async (config) => {
    setLoading(true);
    try {
      const res = await apiFetch('/api/backtest/run', {
        method: 'POST',
        body: JSON.stringify(config)
      });
      if (res.ok) {
        const data = await res.json();
        setBacktestResults(data);
        setActiveTab('backtest');
      }
    } catch (err) {
      console.error('Backtest failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const riskColor = (risk) => {
    if (risk === 'High') return T.red;
    if (risk === 'Moderate') return T.gold;
    return T.green;
  };

  const riskLabel = (risk) => {
    if (risk === 'High') return 'HIGH';
    if (risk === 'Moderate') return 'MOD';
    return 'LOW';
  };

  return (
    <div style={{ borderRadius: 12, overflow: 'hidden', display: 'flex', flexDirection: 'column', background: T.surface, border: `1px solid ${T.border}` }}>
      {/* Tab Header Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', borderBottom: `1px solid ${T.border}`, background: T.bg }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <button
            onClick={() => setActiveTab('engines')}
            style={{
              padding: '6px 12px',
              borderRadius: 6,
              border: activeTab === 'engines' ? `1px solid ${T.borderHi}` : '1px solid transparent',
              background: activeTab === 'engines' ? T.border : 'transparent',
              color: activeTab === 'engines' ? T.accent : T.textDim,
              fontSize: 11,
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              transition: 'all 0.15s ease',
            }}
          >
            <Settings2 size={12} /> ENGINES ({strategies.length})
          </button>
          <button
            onClick={() => setActiveTab('backtest')}
            style={{
              padding: '6px 12px',
              borderRadius: 6,
              border: activeTab === 'backtest' ? `1px solid ${T.borderHi}` : '1px solid transparent',
              background: activeTab === 'backtest' ? T.border : 'transparent',
              color: activeTab === 'backtest' ? T.accent : T.textDim,
              fontSize: 11,
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              transition: 'all 0.15s ease',
            }}
          >
            <BarChart3 size={12} /> BACKTEST
          </button>
          <button
            onClick={() => setActiveTab('accuracy')}
            style={{
              padding: '6px 12px',
              borderRadius: 6,
              border: activeTab === 'accuracy' ? `1px solid ${T.borderHi}` : '1px solid transparent',
              background: activeTab === 'accuracy' ? T.border : 'transparent',
              color: activeTab === 'accuracy' ? T.accent : T.textDim,
              fontSize: 11,
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              transition: 'all 0.15s ease',
            }}
          >
            <ShieldCheck size={12} /> ACCURACY
          </button>
        </div>
      </div>

      {/* 5 PREDICTION ENGINES */}
      {activeTab === 'engines' && (
        <div style={{ padding: 16, maxHeight: 'calc(100vh - 200px)', overflowY: 'auto' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 12 }}>
            {strategies.map((strat) => {
              const isSelected = selectedStrategy === strat.id;
              const Icon = strat.icon;
              const iconColor = ICON_COLORS[strat.id] || T.accent;
              const risk = strat.risk;
              const isHighRisk = risk === 'High';
              const isModRisk = risk === 'Moderate';
              
              return (
                <div
                  key={strat.id}
                  onClick={() => onSelectStrategy?.(strat.id)}
                  style={{
                    padding: 16,
                    borderRadius: 10,
                    background: isSelected ? `${iconColor}08` : T.bg,
                    border: `1px solid ${isSelected ? iconColor + '50' : isHighRisk ? T.red + '30' : isModRisk ? T.gold + '30' : T.green + '30'}`,
                    borderLeft: `3px solid ${iconColor}`,
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    gap: 12,
                    transition: 'all 0.2s ease',
                    boxShadow: isSelected ? `0 0 16px ${iconColor}20` : 'none',
                  }}
                  onMouseEnter={e => !isSelected && (e.currentTarget.style.background = T.panelAlt)}
                  onMouseLeave={e => !isSelected && (e.currentTarget.style.background = T.bg)}
                >
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <div style={{
                          width: 36, height: 36, borderRadius: 8,
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          background: `${iconColor}15`, border: `1px solid ${iconColor}30`,
                        }}>
                          <Icon size={18} color={iconColor} strokeWidth={2.5} />
                        </div>
                        <div>
                          <h4 style={{ fontSize: 14, fontWeight: 800, color: T.text, margin: 0, fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                            {strat.name}
                          </h4>
                          <span style={{ fontSize: 11, color: T.textMid }}>{strat.type}</span>
                        </div>
                      </div>
                      <span style={{
                        padding: '3px 8px',
                        borderRadius: 9999,
                        fontSize: 9,
                        fontWeight: 700,
                        background: isHighRisk ? T.redDim : isModRisk ? T.goldDim : T.greenDim,
                        border: `1px solid ${isHighRisk ? T.red : isModRisk ? T.gold : T.green}`,
                        color: isHighRisk ? T.red : isModRisk ? T.gold : T.green,
                      }}>
                        {riskLabel(risk)}
                      </span>
                    </div>
                    <p style={{ fontSize: 11, color: T.textMid, margin: 0, lineHeight: 1.5 }}>
                      {strat.description}
                    </p>
                  </div>

                  <div style={{
                    paddingTop: 10,
                    borderTop: `1px solid ${T.border}`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between'
                  }}>
                    <span style={{ fontSize: 12, color: T.textMid, fontFamily: "'IBM Plex Mono', monospace" }}>
                      Accuracy: <strong style={{ color: T.text }}>{strat.winRate || '—'}</strong>
                    </span>
                    <span style={{
                      padding: '3px 8px',
                      borderRadius: 4,
                      fontSize: 9,
                      fontWeight: 800,
                      fontFamily: "'IBM Plex Mono', monospace",
                      background: strat.enabled ? `${iconColor}15` : T.panel,
                      border: `1px solid ${strat.enabled ? iconColor + '30' : T.border}`,
                      color: strat.enabled ? iconColor : T.textDim,
                    }}>
                      {strat.enabled ? 'ACTIVE' : 'IDLE'}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* BACKTEST */}
      {activeTab === 'backtest' && (
        <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 16, flex: 1, overflowY: 'auto' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <h3 style={{ fontSize: 13, fontWeight: 700, color: T.text, margin: 0 }}>RUN HISTORICAL BACKTEST</h3>
            
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12 }}>
              <div>
                <label style={{ fontSize: 9, fontWeight: 700, color: T.textMid, display: 'block', marginBottom: 4 }}>SYMBOL</label>
                <select
                  defaultValue="RELIANCE.NS"
                  style={{
                    width: '100%', padding: '8px 10px', background: T.bg, border: `1px solid ${T.border}`, borderRadius: 6, color: T.text, fontSize: 11, outline: 'none'
                  }}
                >
                  <option value="RELIANCE.NS">RELIANCE</option>
                  <option value="TCS.NS">TCS</option>
                  <option value="INFY.NS">INFY</option>
                  <option value="HDFCBANK.NS">HDFCBANK</option>
                  <option value="ICICIBANK.NS">ICICIBANK</option>
                  <option value="SBIN.NS">SBIN</option>
                  <option value="BHARTIARTL.NS">BHARTIARTL</option>
                  <option value="ITC.NS">ITC</option>
                  <option value="KOTAKBANK.NS">KOTAKBANK</option>
                  <option value="LT.NS">LT</option>
                </select>
              </div>
              
              <div>
                <label style={{ fontSize: 9, fontWeight: 700, color: T.textMid, display: 'block', marginBottom: 4 }}>STRATEGY</label>
                <select
                  defaultValue="intraday_momentum"
                  style={{
                    width: '100%', padding: '8px 10px', background: T.bg, border: `1px solid ${T.border}`, borderRadius: 6, color: T.text, fontSize: 11, outline: 'none'
                  }}
                >
                  {STRATEGY_PRESETS.map(s => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
              </div>
              
              <div>
                <label style={{ fontSize: 9, fontWeight: 700, color: T.textMid, display: 'block', marginBottom: 4 }}>YEAR</label>
                <select
                  defaultValue="2024"
                  style={{
                    width: '100%', padding: '8px 10px', background: T.bg, border: `1px solid ${T.border}`, borderRadius: 6, color: T.text, fontSize: 11, outline: 'none'
                  }}
                >
                  <option value="2024">2024</option>
                  <option value="2023">2023</option>
                  <option value="2022">2022</option>
                </select>
              </div>
              
              <div>
                <label style={{ fontSize: 9, fontWeight: 700, color: T.textMid, display: 'block', marginBottom: 4 }}>CAPITAL (₹)</label>
                <input
                  type="number"
                  defaultValue="100000"
                  style={{
                    width: '100%', padding: '8px 10px', background: T.bg, border: `1px solid ${T.border}`, borderRadius: 6, color: T.text, fontSize: 11, outline: 'none'
                  }}
                />
              </div>
              
              <div>
                <label style={{ fontSize: 9, fontWeight: 700, color: T.textMid, display: 'block', marginBottom: 4 }}>STOP ATR</label>
                <input
                  type="number"
                  step="0.1"
                  defaultValue="1.5"
                  style={{
                    width: '100%', padding: '8px 10px', background: T.bg, border: `1px solid ${T.border}`, borderRadius: 6, color: T.text, fontSize: 11, outline: 'none'
                  }}
                />
              </div>
            </div>

            <button
              onClick={(e) => {
                e.preventDefault();
                handleBacktestRun({
                  symbol: 'RELIANCE.NS',
                  strategy: 'intraday_momentum',
                  start_date: '2024-01-01',
                  end_date: '2024-12-31',
                  capital: 100000,
                  stop_atr: 1.5,
                });
              }}
              disabled={loading}
              style={{
                padding: '12px 0',
                background: loading ? T.border : T.accent,
                border: 'none',
                borderRadius: 6,
                color: loading ? T.textDim : T.text,
                fontSize: 11,
                fontWeight: 700,
                cursor: loading ? 'not-allowed' : 'pointer',
                letterSpacing: '0.04em',
                transition: 'all 0.2s',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8
              }}
            >
              {loading ? (
                <>
                  <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} />
                  <span>RUNNING BACKTEST...</span>
                </>
              ) : (
                <>
                  <Zap size={16} />
                  <span>RUN BACKTEST</span>
                </>
              )}
            </button>

            {backtestResults && (
              <div style={{ background: T.bg, border: `1px solid ${T.borderHi}`, borderRadius: 10, padding: 16 }}>
                <h4 style={{ fontSize: 12, fontWeight: 700, color: T.text, marginBottom: 12 }}>BACKTEST RESULTS</h4>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12 }}>
                  {[
                    { label: 'TOTAL RETURN', value: `${backtestResults.total_pnl_pct >= 0 ? '+' : ''}${backtestResults.total_pnl_pct?.toFixed(2)}%`, color: backtestResults.total_pnl_pct >= 0 ? T.green : T.red },
                    { label: 'WIN RATE', value: `${backtestResults.win_rate?.toFixed(1)}%`, color: backtestResults.win_rate >= 50 ? T.green : T.red },
                    { label: 'MAX DD', value: `${backtestResults.max_drawdown?.toFixed(2)}%`, color: T.red },
                    { label: 'SHARPE', value: backtestResults.sharpe_ratio?.toFixed(2), color: T.accent },
                    { label: 'TRADES', value: backtestResults.total_trades?.toString(), color: T.text },
                    { label: 'PROFIT FACTOR', value: backtestResults.profit_factor?.toFixed(2), color: backtestResults.profit_factor >= 1.5 ? T.green : backtestResults.profit_factor >= 1.0 ? T.gold : T.red },
                  ].map(m => (
                    <div key={m.label} style={{ background: T.bg, border: `1px solid ${T.border}`, borderRadius: 8, padding: 12, textAlign: 'center' }}>
                      <div style={{ fontSize: 8, fontWeight: 700, color: T.textMid, letterSpacing: '0.08em', ...mono, marginBottom: 4 }}>{m.label}</div>
                      <div style={{ fontSize: 20, fontWeight: 800, color: m.color, ...mono }}>{m.value}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ACCURACY COMPARISON */}
      {activeTab === 'accuracy' && (
        <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 16, flex: 1, overflowY: 'auto' }}>
          <h3 style={{ fontSize: 13, fontWeight: 700, color: T.text, margin: 0 }}>STRATEGY PREDICTION ACCURACY</h3>
          
          {accuracyData?.leaderboard && accuracyData.leaderboard.length > 0 ? (
            <div style={{ overflowX: 'auto' }}>
              <div style={{ minWidth: '700px' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr 1fr 1fr 1fr 1fr', padding: '8px 12px', borderBottom: `1px solid ${T.border}`, fontSize: 9, color: T.textMid, letterSpacing: '0.08em', ...mono }}>
                  <span>STRATEGY</span>
                  <span>WIN RATE</span>
                  <span>PROFIT FACTOR</span>
                  <span>EXPECTED VALUE</span>
                  <span>RESOLVED</span>
                  <span>STATUS</span>
                </div>
                {accuracyData.leaderboard.map((item, idx) => {
                  const isActive = item.profit_factor >= 1.0;
                  return (
                    <div key={idx} style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr 1fr 1fr 1fr 1fr', padding: '12px 12px', borderBottom: `1px solid ${T.border}`, fontSize: 11, ...mono, alignItems: 'center' }}>
                      <span style={{ color: T.text, fontWeight: 700 }}>{item.setup_type}</span>
                      <span style={{ color: (item.win_rate ?? 0) >= 50 ? T.green : T.textMid }}>{(item.win_rate ?? 0).toFixed(1)}% ({item.wins}/{item.trades})</span>
                      <span style={{ color: (item.profit_factor ?? 0) >= 1.5 ? T.green : (item.profit_factor ?? 0) >= 1.0 ? T.gold : T.red, fontWeight: 700 }}>{(item.profit_factor ?? 0).toFixed(2)}x</span>
                      <span style={{ color: (item.ev_pct ?? 0) > 0 ? T.green : T.red }}>{(item.ev_pct ?? 0) > 0 ? '+' : ''}{(item.ev_pct ?? 0).toFixed(2)}%</span>
                      <span style={{ color: T.text, fontWeight: 600 }}>{item.trades}</span>
                      <span>
                        {isActive ? (
                          <span style={{ background: T.greenDim, color: T.green, padding: '2px 6px', borderRadius: 4, fontSize: 8, fontWeight: 700, border: `1px solid ${T.green}30` }}>ACTIVE</span>
                        ) : (
                          <span style={{ background: T.redDim, color: T.red, padding: '2px 6px', borderRadius: 4, fontSize: 8, fontWeight: 700, border: `1px solid ${T.red}30` }}>LOW PF</span>
                        )}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div style={{ padding: '40px 20px', textAlign: 'center', color: T.textDim, fontSize: 11, ...mono }}>
              No resolved predictions yet. Record predictions and let the resolver track outcomes.<br/>
              <span style={{ fontSize: 10, opacity: 0.7 }}>Accuracy per strategy will appear here once predictions are resolved.</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}