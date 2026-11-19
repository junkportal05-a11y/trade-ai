import { API_BASE_URL } from './api';
import React, { useMemo, useState, useEffect } from 'react';
import { T, mono, fmt, sign } from './theme';

const BASE = API_BASE_URL;

const DEFAULT_WATCHLIST = [
  { symbol: 'YESBANK.NS',    name: 'Yes Bank',       sector: 'Banking' },
  { symbol: 'TATASTEEL.NS',  name: 'Tata Steel',     sector: 'Metals' },
  { symbol: 'BANKBARODA.NS', name: 'Bank of Baroda', sector: 'Banking' },
  { symbol: 'TATAPOWER.NS',  name: 'Tata Power',     sector: 'Power' },
  { symbol: 'SBIN.NS',       name: 'SBI',            sector: 'Banking' },
];

const STRATEGY_PRESETS = [
  { id: 'trend_scalper',      name: 'Trend Scalper',      type: 'Momentum',      risk: 'Moderate', winRate: '54.0%', enabled: true },
  { id: 'mean_reversion',     name: 'Mean Reversion',     type: 'Statistical',   risk: 'Low',      winRate: '58.5%', enabled: true },
  { id: 'breakout_volume',    name: 'Breakout Volume',    type: 'Directional',   risk: 'High',     winRate: '49.8%', enabled: false },
  { id: 'rsi_scalper',        name: 'RSI Scalper',        type: 'Micro Scalp',   risk: 'Moderate', winRate: '52.1%', enabled: false },
  { id: 'swing_trend_follower', name: 'Swing Trend Follower', type: 'Trend Horizon', risk: 'Low',      winRate: '51.2%', enabled: true },
];

export default function HomePanel({ 
  prices, 
  onViewChange, 
  onSelectSymbol, 
  brief, 
  loadingBrief, 
  briefError,
  stats, 
  onRefreshBrief 
}) {
  const [engineStatus, setEngineStatus] = useState('UNKNOWN');
  const [lastScanTime, setLastScanTime] = useState(null);

  // Market Status check (active trading hours 9:15 to 15:30 IST on weekdays)
  const isMarketOpen = useMemo(() => {
    const now = new Date();
    const utc = now.getTime() + (now.getTimezoneOffset() * 60000);
    const ist = new Date(utc + (3600000 * 5.5));
    const day = ist.getDay();
    const hours = ist.getHours();
    const minutes = ist.getMinutes();
    const timeVal = hours * 100 + minutes;
    
    const isWeekday = day >= 1 && day <= 5;
    const isTradingHours = timeVal >= 915 && timeVal <= 1530;
    return isWeekday && isTradingHours;
  }, []);

  // Fetch engine status from backend
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch(`${BASE}/api/bot/status`);
        if (res.ok) {
          const data = await res.json();
          setEngineStatus(data.state || 'UNKNOWN');
          if (data.last_scan_time) {
            setLastScanTime(new Date(data.last_scan_time).toLocaleTimeString('en-IN', { hour12: true, timeZone: 'Asia/Kolkata' }));
          }
        }
      } catch (e) {
        setEngineStatus('OFFLINE');
      }
    };
    
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000); // Poll every 30s
    return () => clearInterval(interval);
  }, []);

  // Find best scanner signal
  const bestSignal = useMemo(() => {
    if (!brief?.top_opportunities || brief.top_opportunities.length === 0) return null;
    return brief.top_opportunities[0];
  }, [brief]);

  return (
    <div style={{ flex: 1, background: T.bg, padding: 24, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 24, boxSizing: 'border-box' }}>
      
      {/* Title */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: `1px solid ${T.border}`, paddingBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.02em', color: T.text, marginBottom: 4 }}> TODAY'S PREDICTION DASHBOARD</h2>
          <p style={{ fontSize: 11, color: T.textMid }}>Market briefing, top predictions, strategy leaderboard, engine status</p>
        </div>
        <div style={{
          padding: '6px 14px',
          background: isMarketOpen ? T.greenDim : T.goldDim,
          border: `1px solid ${isMarketOpen ? T.green : T.gold}30`,
          borderRadius: 6,
          color: isMarketOpen ? T.green : T.gold,
          fontSize: 10,
          fontWeight: 700,
          display: 'flex',
          alignItems: 'center',
          gap: 6
        }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: isMarketOpen ? T.green : T.gold, animation: isMarketOpen ? 'pulse 1.8s infinite' : 'none' }} />
          NSE MARKET: {isMarketOpen ? 'OPEN (IST)' : 'CLOSED'}
        </div>
      </div>

      {/* Daily Market Briefing */}
      <div style={{
        background: T.surface,
        border: `1px solid ${T.border}`,
        borderRadius: 12,
        padding: 20,
        display: 'flex',
        flexDirection: 'column',
        gap: 16
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: `1px solid ${T.border}`, paddingBottom: 12 }}>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', color: T.accentAlt, display: 'flex', alignItems: 'center', gap: 6 }}>
            <span></span> AI DAILY MARKET BRIEFING
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            {onRefreshBrief && (
              <button 
                onClick={onRefreshBrief} 
                disabled={loadingBrief}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: T.accent,
                  fontSize: 9,
                  fontWeight: 700,
                  cursor: loadingBrief ? 'not-allowed' : 'pointer',
                  letterSpacing: '0.04em',
                  padding: 0
                }}
              >
                {loadingBrief ? 'REFRESHING...' : 'REFRESH'}
              </button>
            )}
            <span style={{ fontSize: 9, color: T.textDim, ...mono }}>GENERATED DAILY AT MARKET OPEN</span>
          </div>
        </div>
        
        {loadingBrief ? (
          <div style={{ padding: '20px 0', textAlign: 'center', fontSize: 11, color: T.textDim }}>
            <span style={{ display: 'inline-block', width: 14, height: 14, border: `1.5px solid ${T.border}`, borderTopColor: T.accentAlt, borderRadius: '50%', animation: 'spin 0.7s linear infinite', marginRight: 8, verticalAlign: 'middle' }} />
            Analyzing watchlist indicators and macro calendar...
            {briefError && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, alignItems: 'center', marginTop: 10 }}>
                <div style={{ color: T.textMid }}>{briefError}</div>
                {onRefreshBrief && (
                  <button
                    onClick={onRefreshBrief}
                    style={{
                      background: 'transparent',
                      border: `1px solid ${T.accent}40`,
                      borderRadius: 6,
                      color: T.accent,
                      fontSize: 10,
                      fontWeight: 700,
                      cursor: 'pointer',
                      letterSpacing: '0.04em',
                      padding: '5px 16px'
                    }}
                  >
                    RETRY
                  </button>
                )}
              </div>
            )}
          </div>
        ) : brief ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {/* Top row metrics */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
              {/* Trend bias */}
              <div style={{ background: T.panelAlt, border: `1px solid ${T.border}`, padding: 12, borderRadius: 8 }}>
                <span style={{ display: 'block', fontSize: 8, color: T.textDim, fontWeight: 700, marginBottom: 4 }}>NIFTY BIAS INDEX</span>
                <span style={{
                  fontSize: 14,
                  fontWeight: 800,
                  color: brief.nifty_trend === 'BULLISH' ? T.green : brief.nifty_trend === 'BEARISH' ? T.red : T.gold
                }}>
                  {brief.nifty_trend === 'BULLISH' ? 'BULLISH' : brief.nifty_trend === 'BEARISH' ? 'BEARISH' : 'CONSOLIDATION'}
                </span>
              </div>
              
              {/* Sentiment Gauge */}
              <div style={{ background: T.panelAlt, border: `1px solid ${T.border}`, padding: 12, borderRadius: 8 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontSize: 8, color: T.textDim, fontWeight: 700 }}>WATCHLIST SENTIMENT</span>
                  <span style={{ fontSize: 10, fontWeight: 700, color: T.gold, ...mono }}>{brief.market_sentiment_pct}% Bullish</span>
                </div>
                <div style={{ height: 6, background: T.border, borderRadius: 3, overflow: 'hidden' }}>
                  <div style={{ width: `${brief.market_sentiment_pct}%`, height: '100%', background: `linear-gradient(90deg, ${T.accent}, ${T.gold})` }} />
                </div>
              </div>

              {/* Opportunities mini block */}
              <div style={{ background: T.panelAlt, border: `1px solid ${T.border}`, padding: 12, borderRadius: 8 }}>
                <span style={{ display: 'block', fontSize: 8, color: T.textDim, fontWeight: 700, marginBottom: 4 }}>TOP PICKS</span>
                <div style={{ display: 'flex', gap: 6 }}>
                  {brief.top_opportunities.map(op => (
                    <span key={op.symbol} onClick={() => { onSelectSymbol(`${op.symbol}.NS`); onViewChange('CHART'); }} style={{
                      fontSize: 9,
                      fontWeight: 700,
                      color: op.signal.includes('BUY') ? T.green : T.red,
                      background: op.signal.includes('BUY') ? T.greenDim : T.redDim,
                      padding: '2px 6px',
                      borderRadius: 4,
                      cursor: 'pointer',
                      border: `1px solid ${op.signal.includes('BUY') ? T.green : T.red}20`
                    }}>
                      {op.symbol} ({op.confidence}%)
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* AI Summary Block */}
            <div style={{ fontSize: 12, color: T.text, lineHeight: 1.6, background: T.panelAlt, border: `1px solid ${T.border}`, padding: '12px 14px', borderRadius: 8 }}>
              {brief.briefing_text}
            </div>

            {/* Risk Events list */}
            {brief.risk_events && brief.risk_events.length > 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <div style={{ fontSize: 9, fontWeight: 700, color: T.textMid, letterSpacing: '0.04em' }}>DAILY MACRO / RISK CALENDAR EVENTS</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  {brief.risk_events.map((evt, idx) => (
                    <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 10, color: T.textMid }}>
                      <span style={{ width: 4, height: 4, background: T.red, borderRadius: '50%' }} />
                      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{evt}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, alignItems: 'center', padding: '10px 0' }}>
            <div style={{ fontSize: 11, color: T.textMid, textAlign: 'center' }}>
              {briefError || 'Failed to fetch Daily Market Briefing. Check connection.'}
            </div>
            {onRefreshBrief && (
              <button
                onClick={onRefreshBrief}
                style={{
                  background: 'transparent',
                  border: `1px solid ${T.accent}40`,
                  borderRadius: 6,
                  color: T.accent,
                  fontSize: 10,
                  fontWeight: 700,
                  cursor: 'pointer',
                  letterSpacing: '0.04em',
                  padding: '5px 16px'
                }}
              >
                RETRY
              </button>
            )}
          </div>
        )}
      </div>

      {/* Grid Layout - Row 1 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 24 }}>
        
        {/* Card 1: Top Screening Trigger */}
        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 12, padding: 20, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', color: T.textMid, marginBottom: 12 }}>TOP SCREENING TRIGGER</div>
            {bestSignal ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 14, fontWeight: 700, color: T.text, ...mono }}>{bestSignal.symbol.replace('.NS', '')}</span>
                  <span style={{
                    fontSize: 9,
                    fontWeight: 700,
                    color: bestSignal.signal.includes('BUY') ? T.green : T.red,
                    background: bestSignal.signal.includes('BUY') ? T.greenDim : T.redDim,
                    padding: '2px 8px',
                    borderRadius: 4
                  }}>
                    {bestSignal.signal}
                  </span>
                </div>
                <div style={{ fontSize: 11, color: T.textMid, lineHeight: 1.4 }}>
                  {bestSignal.reasoning || `Confidence rating is ${bestSignal.confidence}%.`}
                </div>
              </div>
            ) : (
              <div style={{ fontSize: 11, color: T.textDim, lineHeight: 1.4 }}>
                No active technical triggers available. Run a fresh quantitative scan in the Scanner to populate signals.
              </div>
            )}
          </div>
          <button
            onClick={() => onViewChange('SIGNALS')}
            style={{
              marginTop: 16,
              width: '100%',
              padding: '8px 0',
              background: T.goldDim,
              border: `1px solid ${T.accent}30`,
              borderRadius: 6,
              color: T.accent,
              fontSize: 10,
              fontWeight: 700,
              cursor: 'pointer',
              transition: 'all 0.2s',
              letterSpacing: '0.04em'
            }}
            onMouseEnter={e => e.currentTarget.style.background = T.accentDim}
            onMouseLeave={e => e.currentTarget.style.background = T.goldDim}
          >
            OPEN SIGNAL SCANNER
          </button>
        </div>

        {/* Card 2: Predictions Accuracy */}
        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 12, padding: 20, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', color: T.textMid, marginBottom: 12 }}>PREDICTIONS ACCURACY</div>
            {stats ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 24, fontWeight: 800, color: stats.win_rate >= 50 ? T.green : T.red, ...mono }}>
                    {stats.win_rate.toFixed(1)}%
                  </span>
                  <span style={{ fontSize: 10, color: T.textDim }}>Win Rate</span>
                </div>
                <div style={{ height: 6, background: T.border, borderRadius: 3, overflow: 'hidden' }}>
                  <div style={{ width: `${stats.win_rate}%`, height: '100%', background: stats.win_rate >= 50 ? T.green : T.red }} />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: T.textMid, marginTop: 4 }}>
                  <span>Resolved: <strong style={{ color: T.text, ...mono }}>{stats.resolved_predictions}</strong> / <strong style={{ color: T.text, ...mono }}>{stats.total_predictions}</strong></span>
                  <span>MAE: <strong style={{ color: T.gold, ...mono }}>₹{fmt(stats.avg_error)}</strong></span>
                </div>
              </div>
            ) : (
              <div style={{ fontSize: 11, color: T.textDim, lineHeight: 1.4 }}>
                No resolved predictions yet. Open Prediction Center to log your first thesis.
              </div>
            )}
          </div>
          <button
            onClick={() => onViewChange('PREDICTIONS')}
            style={{
              marginTop: 16,
              width: '100%',
              padding: '8px 0',
              background: T.goldDim,
              border: `1px solid ${T.accent}30`,
              borderRadius: 6,
              color: T.accent,
              fontSize: 10,
              fontWeight: 700,
              cursor: 'pointer',
              transition: 'all 0.2s',
              letterSpacing: '0.04em'
            }}
            onMouseEnter={e => e.currentTarget.style.background = T.accentDim}
            onMouseLeave={e => e.currentTarget.style.background = T.goldDim}
          >
            PREDICTIONS CENTRE
          </button>
        </div>

        {/* Card 3: Engine Status */}
        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 12, padding: 20, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', color: T.textMid, marginBottom: 12 }}>PREDICTION ENGINE STATUS</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 11, color: T.text }}>Loop Status</span>
                <span style={{
                  fontSize: 10,
                  fontWeight: 700,
                  color: engineStatus === 'RUNNING' ? T.green : engineStatus === 'PAUSED' ? T.gold : T.red,
                  background: engineStatus === 'RUNNING' ? T.greenDim : engineStatus === 'PAUSED' ? T.goldDim : T.redDim,
                  padding: '2px 8px',
                  borderRadius: 4,
                  border: `1px solid ${engineStatus === 'RUNNING' ? T.green : engineStatus === 'PAUSED' ? T.gold : T.red}30`
                }}>
                  {engineStatus}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 10, color: T.textMid, ...mono }}>
                <span>Last Scan</span>
                <span style={{ color: T.text }}>{lastScanTime || '—'}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 10, color: T.textMid, ...mono }}>
                <span>Feed</span>
                <span style={{ color: T.green }}>LIVE</span>
              </div>
            </div>
          </div>
        </div>

      </div>

      {/* Row 2: Strategy Leaderboard */}
      <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 12, padding: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, borderBottom: `1px solid ${T.border}`, paddingBottom: 10 }}>
          <h3 style={{ fontSize: 13, fontWeight: 700, letterSpacing: '0.04em', color: T.text, margin: 0 }}>
            STRATEGY LEADERBOARD (PREDICTION ACCURACY)
          </h3>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <div style={{ minWidth: '700px' }}>
            {/* Header */}
            <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr 1fr 1fr 1fr', padding: '8px 12px', borderBottom: `1px solid ${T.border}`, fontSize: 9, color: T.textMid, letterSpacing: '0.08em', ...mono }}>
              <span>STRATEGY</span>
              <span>TYPE</span>
              <span>RISK</span>
              <span>WIN RATE</span>
              <span>STATUS</span>
            </div>
            
            {/* Rows */}
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              {STRATEGY_PRESETS.map((strat, idx) => {
                const statsData = stats?.leaderboard?.find(s => s.setup_type === strat.name);
                const isActive = strat.enabled;
                const winRate = statsData?.win_rate ?? strat.winRate;
                return (
                  <div key={strat.id} style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr 1fr 1fr 1fr', padding: '12px 12px', borderBottom: `1px solid ${T.border}`, fontSize: 11, ...mono, alignItems: 'center' }}>
                    <span style={{ color: T.text, fontWeight: 700 }}>{strat.name}</span>
                    <span style={{ color: T.textMid }}>{strat.type}</span>
                    <span style={{ color: strat.risk === 'High' ? T.red : strat.risk === 'Moderate' ? T.gold : T.green, fontWeight: 600 }}>{strat.risk}</span>
                    <span style={{ color: parseFloat(winRate) >= 50 ? T.green : T.textMid, fontWeight: 700 }}>{winRate}</span>
                    <span>
                      {isActive ? (
                        <span style={{ background: T.greenDim, color: T.green, padding: '2px 6px', borderRadius: 4, fontSize: 8, fontWeight: 700, border: `1px solid ${T.green}30` }}>ENABLED</span>
                      ) : (
                        <span style={{ background: T.redDim, color: T.red, padding: '2px 6px', borderRadius: 4, fontSize: 8, fontWeight: 700, border: `1px solid ${T.red}30` }}>DISABLED</span>
                      )}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Row 3: Links to main sections */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16, marginTop: 8 }}>
        <button
          onClick={() => onViewChange('CHART')}
          style={{
            padding: '20px 16px',
            background: T.surface,
            border: `1px solid ${T.border}`,
            borderRadius: 12,
            cursor: 'pointer',
            transition: 'all 0.2s',
            display: 'flex',
            flexDirection: 'column',
            gap: 8,
            textAlign: 'left'
          }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = T.accent; e.currentTarget.style.background = T.panelAlt; }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = T.border; e.currentTarget.style.background = T.surface; }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 18 }}>📈</span>
            <span style={{ fontSize: 13, fontWeight: 700, color: T.text }}>INTERACTIVE CHARTS</span>
          </div>
          <span style={{ fontSize: 11, color: T.textMid }}>Candles, indicators, AI Analyst read</span>
        </button>

        <button
          onClick={() => onViewChange('PREDICTIONS')}
          style={{
            padding: '20px 16px',
            background: T.surface,
            border: `1px solid ${T.border}`,
            borderRadius: 12,
            cursor: 'pointer',
            transition: 'all 0.2s',
            display: 'flex',
            flexDirection: 'column',
            gap: 8,
            textAlign: 'left'
          }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = T.accent; e.currentTarget.style.background = T.panelAlt; }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = T.border; e.currentTarget.style.background = T.surface; }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 18 }}>🎯</span>
            <span style={{ fontSize: 13, fontWeight: 700, color: T.text }}>PREDICTION ENGINE</span>
          </div>
          <span style={{ fontSize: 11, color: T.textMid }}>AI predictions + tracking + accuracy</span>
        </button>

        <button
          onClick={() => onViewChange('STRATEGIES')}
          style={{
            padding: '20px 16px',
            background: T.surface,
            border: `1px solid ${T.border}`,
            borderRadius: 12,
            cursor: 'pointer',
            transition: 'all 0.2s',
            display: 'flex',
            flexDirection: 'column',
            gap: 8,
            textAlign: 'left'
          }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = T.accent; e.currentTarget.style.background = T.panelAlt; }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = T.border; e.currentTarget.style.background = T.surface; }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 18 }}>⚙️</span>
            <span style={{ fontSize: 13, fontWeight: 700, color: T.text }}>STRATEGY BACKTESTS</span>
          </div>
          <span style={{ fontSize: 11, color: T.textMid }}>5 engines + backtest + accuracy comparison</span>
        </button>
      </div>

    </div>
  );
}