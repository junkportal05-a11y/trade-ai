import React, { useMemo, useState, useEffect } from 'react';

const BASE = import.meta.env.VITE_API_URL || "https://trade-ai-nkqv.onrender.com";

const T = {
  bg:         '#080a0f',
  surface:    '#0d1018',
  panel:      '#111520',
  panelAlt:   '#0f1219',
  border:     '#1a1f2e',
  borderHi:   '#252c40',
  text:       '#d0d8ed',
  textMid:    '#6e7a96',
  textDim:    '#363d55',
  green:      '#00e5a8',
  greenDim:   'rgba(0,229,168,0.1)',
  red:        '#ff3d5a',
  redDim:     'rgba(255,61,90,0.1)',
  blue:       '#4da6ff',
  blueDim:    'rgba(77,166,255,0.1)',
  gold:       '#f5c842',
  goldDim:    'rgba(245,200,66,0.1)',
  accent:     '#7b6cff',
  accentAlt:  '#9b5de5',
};

const mono = { fontFamily: "'IBM Plex Mono', monospace" };
const fmt = (n, d = 2) => n == null ? '—' : Number(n).toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d });
const sign = (v) => v > 0 ? '+' : '';

const DEFAULT_WATCHLIST = [
  { symbol: 'HAL.NS',        name: 'HAL',            sector: 'Defence' },
  { symbol: 'BEL.NS',        name: 'BEL',            sector: 'Defence' },
  { symbol: 'RVNL.NS',       name: 'RVNL',           sector: 'Railways' },
  { symbol: 'IREDA.NS',      name: 'IREDA',          sector: 'Green Energy' },
  { symbol: 'HUDCO.NS',      name: 'HUDCO',          sector: 'Finance' },
  { symbol: 'COALINDIA.NS',  name: 'Coal India',     sector: 'Energy' },
  { symbol: 'NHPC.NS',       name: 'NHPC',           sector: 'Power' },
  { symbol: 'ADANIPORTS.NS', name: 'Adani Ports',    sector: 'Infrastructure' },
  { symbol: 'TATAPOWER.NS',  name: 'Tata Power',     sector: 'Power' },
  { symbol: 'BHEL.NS',       name: 'BHEL',           sector: 'Capital Goods' },
  { symbol: 'RELIANCE.NS',   name: 'Reliance',       sector: 'Energy' },
  { symbol: 'TCS.NS',        name: 'TCS',            sector: 'IT' },
  { symbol: 'HDFCBANK.NS',   name: 'HDFC Bank',      sector: 'Banking' },
  { symbol: 'INFY.NS',       name: 'Infosys',        sector: 'IT' },
  { symbol: 'ICICIBANK.NS',  name: 'ICICI Bank',     sector: 'Banking' },
  { symbol: 'SBIN.NS',       name: 'SBI',            sector: 'Banking' },
  { symbol: 'TATAMOTORS.NS', name: 'Tata Motors',    sector: 'Auto' },
  { symbol: 'BHARTIARTEL.NS',name: 'Bharti Airtel',   sector: 'Telecom' },
  { symbol: 'ITC.NS',        name: 'ITC',            sector: 'FMCG' },
  { symbol: 'LT.NS',         name: 'L&T',            sector: 'Infrastructure' },
  { symbol: 'ADANIENT.NS',   name: 'Adani Ent',      sector: 'Conglomerate' },
  { symbol: 'ADANIPOWER.NS', name: 'Adani Power',    sector: 'Power' },
  { symbol: 'IRFC.NS',       name: 'IRFC',           sector: 'Railways' },
  { symbol: 'PFC.NS',        name: 'PFC',            sector: 'Finance' },
  { symbol: 'REC.NS',        name: 'REC',            sector: 'Finance' },
  { symbol: 'ZOMATO.NS',     name: 'Zomato',         sector: 'Consumer Tech' },
  { symbol: 'TATASTEEL.NS',  name: 'Tata Steel',     sector: 'Metals' },
  { symbol: 'SAIL.NS',       name: 'SAIL',           sector: 'Metals' },
  { symbol: 'WIPRO.NS',      name: 'Wipro',          sector: 'IT' },
  { symbol: 'JIOFIN.NS',     name: 'Jio Financial',  sector: 'Finance' },
  { symbol: 'SJVN.NS',       name: 'SJVN',           sector: 'Power' },
  { symbol: 'GMRINFRA.NS',   name: 'GMR Infra',      sector: 'Infrastructure' },
  { symbol: 'NBCC.NS',       name: 'NBCC',           sector: 'Infrastructure' },
  { symbol: 'JINDALSTEL.NS', name: 'Jindal Steel',   sector: 'Metals' },
  { symbol: 'JSWSTEEL.NS',   name: 'JSW Steel',      sector: 'Metals' },
  { symbol: 'HINDALCO.NS',   name: 'Hindalco',       sector: 'Metals' },
  { symbol: 'BPCL.NS',       name: 'BPCL',           sector: 'Energy' },
  { symbol: 'IOC.NS',        name: 'IOC',            sector: 'Energy' },
  { symbol: 'ONGC.NS',       name: 'ONGC',           sector: 'Energy' },
  { symbol: 'NTPC.NS',       name: 'NTPC',           sector: 'Power' },
];

export default function HomePanel({ 
  prices, 
  portfolio, 
  cash, 
  onViewChange, 
  onSelectSymbol, 
  signals = [], 
  priceAlerts = [], 
  onDeleteAlert, 
  brief, 
  loadingBrief, 
  stats, 
  onRefreshBrief, 
  onUpdateBalances 
}) {
  const [showEditModal, setShowEditModal] = useState(false);
  const [tempCash, setTempCash] = useState(cash);
  const [tempPortfolio, setTempPortfolio] = useState([]);
  const [newHoldingSymbol, setNewHoldingSymbol] = useState('HAL.NS');
  const [newHoldingShares, setNewHoldingShares] = useState('');
  const [newHoldingAvgCost, setNewHoldingAvgCost] = useState('');

  const handleOpenEditModal = () => {
    setTempCash(cash);
    setTempPortfolio(portfolio.map(p => ({ ...p })));
    setShowEditModal(true);
  };

  const handleAddHolding = () => {
    const shares = parseFloat(newHoldingShares);
    const cost = parseFloat(newHoldingAvgCost);
    if (!newHoldingSymbol || isNaN(shares) || shares <= 0 || isNaN(cost) || cost <= 0) return;
    
    const idx = tempPortfolio.findIndex(p => p.symbol === newHoldingSymbol);
    if (idx >= 0) {
      const updated = [...tempPortfolio];
      const newTotalShares = updated[idx].shares + shares;
      const newAvgCost = ((updated[idx].avgCost * updated[idx].shares) + (cost * shares)) / newTotalShares;
      updated[idx] = { symbol: newHoldingSymbol, shares: newTotalShares, avgCost: Math.round(newAvgCost * 100) / 100 };
      setTempPortfolio(updated);
    } else {
      setTempPortfolio(prev => [...prev, { symbol: newHoldingSymbol, shares, avgCost: cost }]);
    }
    setNewHoldingShares('');
    setNewHoldingAvgCost('');
  };

  const handleRemoveHolding = (symbol) => {
    setTempPortfolio(prev => prev.filter(p => p.symbol !== symbol));
  };

  const handleSaveBalances = () => {
    const nextCash = parseFloat(tempCash);
    if (isNaN(nextCash) || nextCash < 0) return;
    if (onUpdateBalances) {
      onUpdateBalances(nextCash, tempPortfolio);
    }
    setShowEditModal(false);
  };
  
  // Calculate Portfolio Value
  const { stockValue, totalValue, totalPnl, totalPct } = useMemo(() => {
    let stockVal = 0;
    let totalCost = 0;
    
    portfolio.forEach(pos => {
      const price = prices[pos.symbol]?.price ?? pos.avgCost;
      stockVal += price * pos.shares;
      totalCost += pos.avgCost * pos.shares;
    });
    
    const totVal = stockVal + cash;
    const pnl = stockVal - totalCost;
    const pct = totalCost > 0 ? (pnl / totalCost) * 100 : 0;
    
    return { stockValue: stockVal, totalValue: totVal, totalPnl: pnl, totalPct: pct };
  }, [portfolio, prices, cash]);

  // Donut chart calculation
  const C = 157.08; // Circumference for R=25
  const slices = useMemo(() => {
    const s = [];
    let accWeight = 0;
    
    if (totalValue > 0) {
      const cashWeight = cash / totalValue;
      s.push({
        label: 'Cash',
        value: cash,
        color: T.blue,
        weight: cashWeight,
        dashOffset: C - (accWeight * C),
      });
      accWeight += cashWeight;
    }
    
    const COLORS = ['#7b6cff', '#00e5a8', '#ff9f43', '#9b5de5', '#f5c842', '#ff3d5a', '#ff4da6'];
    portfolio.forEach((pos, idx) => {
      const price = prices[pos.symbol]?.price ?? pos.avgCost;
      const val = price * pos.shares;
      if (totalValue > 0 && val > 0) {
        const weight = val / totalValue;
        s.push({
          label: pos.symbol.replace('.NS', ''),
          value: val,
          color: COLORS[idx % COLORS.length],
          weight,
          dashOffset: C - (accWeight * C),
        });
        accWeight += weight;
      }
    });
    return s;
  }, [portfolio, prices, cash, totalValue]);

  // Find best scanner signal (BUY / SELL with highest confidence)
  const bestSignal = useMemo(() => {
    if (!signals || signals.length === 0) return null;
    return [...signals].sort((a, b) => (b.confidence || 0) - (a.confidence || 0))[0];
  }, [signals]);

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

  return (
    <div style={{ flex: 1, background: T.bg, padding: 24, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 24, boxSizing: 'border-box' }}>
      
      {/* Title */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: `1px solid ${T.border}`, paddingBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.02em', color: '#fff', marginBottom: 4 }}>📈 QUANT OPERATIONS CENTRE</h2>
          <p style={{ fontSize: 11, color: T.textMid }}>Active workspace metrics, portfolio weights, and AI mentor insights.</p>
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
            <span>🧠</span> AI DAILY MARKET BRIEFING
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
                {loadingBrief ? '⏳ REFRESHING...' : '🔄 REFRESH'}
              </button>
            )}
            <span style={{ fontSize: 9, color: T.textDim, ...mono }}>GENERATED DAILY AT MARKET OPEN</span>
          </div>
        </div>
        
        {loadingBrief ? (
          <div style={{ padding: '20px 0', textAlign: 'center', fontSize: 11, color: T.textDim }}>
            <span style={{ display: 'inline-block', width: 14, height: 14, border: `1.5px solid ${T.border}`, borderTopColor: T.accentAlt, borderRadius: '50%', animation: 'spin 0.7s linear infinite', marginRight: 8, verticalAlign: 'middle' }} />
            Analyzing watchlist indicators and macro calendar...
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
                  {brief.nifty_trend === 'BULLISH' ? '▲ BULLISH' : brief.nifty_trend === 'BEARISH' ? '▼ BEARISH' : '◆ CONSOLIDATION'}
                </span>
              </div>
              
              {/* Sentiment Gauge */}
              <div style={{ background: T.panelAlt, border: `1px solid ${T.border}`, padding: 12, borderRadius: 8 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontSize: 8, color: T.textDim, fontWeight: 700 }}>WATCHLIST SENTIMENT</span>
                  <span style={{ fontSize: 10, fontWeight: 700, color: T.blue, ...mono }}>{brief.market_sentiment_pct}% Bullish</span>
                </div>
                <div style={{ height: 6, background: T.border, borderRadius: 3, overflow: 'hidden' }}>
                  <div style={{ width: `${brief.market_sentiment_pct}%`, height: '100%', background: `linear-gradient(90deg, ${T.accent}, ${T.blue})` }} />
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
                <div style={{ fontSize: 9, fontWeight: 700, color: T.textMid, letterSpacing: '0.04em' }}>⚠️ DAILY MACRO / RISK CALENDAR EVENTS</div>
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
          <div style={{ fontSize: 11, color: T.textDim, padding: '10px 0', textAlign: 'center' }}>
            Failed to fetch Daily Market Briefing. Check connection.
          </div>
        )}
      </div>

      {/* Grid Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 24 }}>
        
        {/* Card 1: Net Worth Overview */}
        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 12, padding: 20, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', color: T.textMid }}>PORTFOLIO BALANCES</span>
              <button 
                onClick={handleOpenEditModal}
                style={{
                  background: 'rgba(123, 108, 255, 0.08)',
                  border: `1px solid ${T.accent}40`,
                  borderRadius: 4,
                  padding: '2px 8px',
                  color: T.accent,
                  fontSize: 9,
                  fontWeight: 700,
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  letterSpacing: '0.04em'
                }}
                onMouseEnter={e => e.currentTarget.style.background = 'rgba(123, 108, 255, 0.15)'}
                onMouseLeave={e => e.currentTarget.style.background = 'rgba(123, 108, 255, 0.08)'}
              >
                ✏️ ADJUST BALANCE
              </button>
            </div>
            <div 
              onClick={handleOpenEditModal}
              title="Click to adjust Available Cash or add mock positions"
              style={{ fontSize: 28, fontWeight: 800, color: '#fff', letterSpacing: '-0.03em', cursor: 'pointer', display: 'inline-block', transition: 'color 0.2s', ...mono }}
              onMouseEnter={e => e.currentTarget.style.color = T.accent}
              onMouseLeave={e => e.currentTarget.style.color = '#fff'}
            >
              ₹{fmt(totalValue)}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4 }}>
              <span style={{ fontSize: 11, color: totalPnl >= 0 ? T.green : T.red, fontWeight: 700, ...mono }}>
                {sign(totalPnl)}₹{fmt(Math.abs(totalPnl))} ({sign(totalPct)}{fmt(totalPct, 2)}%)
              </span>
              <span style={{ fontSize: 10, color: T.textDim }}>Total P&L</span>
              <span style={{ fontSize: 8, color: T.textMid, marginLeft: 8, fontStyle: 'italic', cursor: 'pointer' }} onClick={handleOpenEditModal}>(Click balance to edit)</span>
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, borderTop: `1px solid ${T.border}`, paddingTop: 16, marginTop: 20 }}>
            <div>
              <div style={{ fontSize: 9, color: T.textDim }}>AVAILABLE CASH</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: T.blue, ...mono }}>₹{fmt(cash)}</div>
            </div>
            <div>
              <div style={{ fontSize: 9, color: T.textDim }}>STOCKS HOLDINGS</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: T.text, ...mono }}>₹{fmt(stockValue)}</div>
            </div>
          </div>
        </div>

        {/* Card 2: Asset Allocation Donut */}
        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 12, padding: 20 }}>
          <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', color: T.textMid, marginBottom: 12 }}>HOLDINGS ALLOCATION</div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-around', gap: 16 }}>
            <svg width="76" height="76" viewBox="0 0 80 80" style={{ transform: 'rotate(-90deg)', flexShrink: 0 }}>
              <circle cx="40" cy="40" r="25" stroke={T.borderHi} strokeWidth="8" fill="transparent" />
              {slices.map((slice, idx) => (
                <circle
                  key={idx}
                  cx="40"
                  cy="40"
                  r="25"
                  stroke={slice.color}
                  strokeWidth="8"
                  fill="transparent"
                  strokeDasharray={`${slice.weight * C} ${C}`}
                  strokeDashoffset={-slice.dashOffset + C}
                  style={{ transition: 'stroke-dashoffset 0.6s ease' }}
                />
              ))}
            </svg>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, flex: 1, minWidth: 0, maxHeight: 110, overflowY: 'auto' }}>
              {slices.map((slice, idx) => (
                <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 9, ...mono }}>
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: slice.color, display: 'inline-block', flexShrink: 0 }} />
                  <span style={{ color: T.textMid, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{slice.label}</span>
                  <span style={{ color: T.text, fontWeight: 600 }}>{(slice.weight * 100).toFixed(0)}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Card 3: Best Signal Highlight */}
        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 12, padding: 20, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', color: T.textMid, marginBottom: 12 }}>TOP SCREENING TRIGGER</div>
            {bestSignal ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 14, fontWeight: 700, color: '#fff', ...mono }}>{bestSignal.symbol.replace('.NS', '')}</span>
                  <span style={{
                    fontSize: 9,
                    fontWeight: 700,
                    color: bestSignal.signal.includes('BUY') ? T.green : T.red,
                    background: bestSignal.signal.includes('BUY') ? 'rgba(0,229,168,0.1)' : 'rgba(255,61,90,0.1)',
                    padding: '2px 8px',
                    borderRadius: 4
                  }}>
                    {bestSignal.signal}
                  </span>
                </div>
                <div style={{ fontSize: 11, color: T.textMid, lineHeight: 1.4 }}>
                  {bestSignal.reasoning || `Confidence rating is ${bestSignal.confidence}%. R:R ratio sits at 1:${bestSignal.rr_ratio}.`}
                </div>
              </div>
            ) : (
              <div style={{ fontSize: 11, color: T.textDim, lineHeight: 1.4 }}>
                No active technical triggers available. Run a fresh quantitative scan in the Signals panel to populate signals.
              </div>
            )}
          </div>
          <button
            onClick={() => onViewChange('SIGNALS')}
            style={{
              marginTop: 16,
              width: '100%',
              padding: '8px 0',
              background: 'rgba(123, 108, 255, 0.08)',
              border: `1px solid ${T.accent}30`,
              borderRadius: 6,
              color: T.accent,
              fontSize: 10,
              fontWeight: 700,
              cursor: 'pointer',
              transition: 'all 0.2s',
              letterSpacing: '0.04em'
            }}
            onMouseEnter={e => e.currentTarget.style.background = 'rgba(123, 108, 255, 0.15)'}
            onMouseLeave={e => e.currentTarget.style.background = 'rgba(123, 108, 255, 0.08)'}
          >
            🛰️ OPEN SIGNAL SCANNER
          </button>
        </div>

        {/* Card 4: Predictions Accuracy */}
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
                  <span>MAE: <strong style={{ color: T.blue, ...mono }}>₹{fmt(stats.avg_error)}</strong></span>
                  <span>Resolved: <strong style={{ color: T.text, ...mono }}>{stats.resolved_predictions}</strong></span>
                </div>
              </div>
            ) : (
              <div style={{ fontSize: 11, color: T.textDim, lineHeight: 1.4 }}>
                No active predictions records. Open Prediction Center to log your first thesis.
              </div>
            )}
          </div>
          <button
            onClick={() => onViewChange('PREDICTIONS')}
            style={{
              marginTop: 16,
              width: '100%',
              padding: '8px 0',
              background: 'rgba(245, 200, 66, 0.08)',
              border: `1px solid ${T.gold}30`,
              borderRadius: 6,
              color: T.gold,
              fontSize: 10,
              fontWeight: 700,
              cursor: 'pointer',
              transition: 'all 0.2s',
              letterSpacing: '0.04em'
            }}
            onMouseEnter={e => e.currentTarget.style.background = 'rgba(245, 200, 66, 0.15)'}
            onMouseLeave={e => e.currentTarget.style.background = 'rgba(245, 200, 66, 0.08)'}
          >
            🔮 PREDICTIONS CENTRE
          </button>
        </div>

      </div>

      {/* Row 2: AI Mentor Pulse & Price Alerts */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 24, marginTop: 8 }}>
        
        {/* AI Quant Recommendation */}
        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 12, padding: 20, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', color: T.textMid, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', background: T.green }} />
              AI QUANT MENTOR RECOMMENDATION
            </div>
            <div style={{ fontSize: 12, color: T.text, lineHeight: 1.6, background: T.panelAlt, border: `1px solid ${T.border}`, padding: '12px 14px', borderRadius: 8 }}>
              💡 <strong>Intraday Sizing Pulse:</strong> Market breadth is testing key resistance blocks. Maintain strict position allocations. Do not deploy more than 2% of simulated capital per stock. Set stop losses below pivot averages to prevent standard sweeps.
            </div>
          </div>
          <button
            onClick={() => {
              onSelectSymbol(bestSignal?.symbol || 'RELIANCE.NS');
              onViewChange('CHART');
            }}
            style={{
              marginTop: 16,
              width: '100%',
              padding: '8px 0',
              background: T.accent,
              border: 'none',
              borderRadius: 6,
              color: '#fff',
              fontSize: 10,
              fontWeight: 700,
              cursor: 'pointer',
              transition: 'all 0.2s',
              letterSpacing: '0.04em'
            }}
            onMouseEnter={e => e.currentTarget.style.background = '#6c5ce7'}
            onMouseLeave={e => e.currentTarget.style.background = T.accent}
          >
            📈 OPEN INTERACTIVE CHARTS
          </button>
        </div>

        {/* Quick Price Alerts */}
        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 12, padding: 20, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', color: T.textMid, marginBottom: 12 }}>ACTIVE PRICE ALERTS</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 110, overflowY: 'auto' }}>
              {priceAlerts.length === 0 ? (
                <div style={{ fontSize: 11, color: T.textDim, padding: '10px 0', textAlign: 'center' }}>
                  No active price alerts set. Use the order sidebar in the Charts tab to place alerts.
                </div>
              ) : (
                priceAlerts.map(alert => (
                  <div key={alert.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: T.panelAlt, border: `1px solid ${T.border}`, padding: '6px 10px', borderRadius: 6, fontSize: 10, ...mono }}>
                    <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                      <span style={{ color: T.text, fontWeight: 700 }}>{alert.symbol.replace('.NS', '')}</span>
                      <span style={{ color: alert.condition === 'above' ? T.green : T.red }}>
                        {alert.condition === 'above' ? '≥' : '≤'} ₹{fmt(alert.targetPrice, 1)}
                      </span>
                    </div>
                    <button
                      onClick={() => onDeleteAlert(alert.id)}
                      style={{ background: 'none', border: 'none', color: T.red, cursor: 'pointer', fontSize: 9, fontWeight: 700 }}
                    >
                      REMOVE
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

      </div>

      {/* Edit Balance Modal */}
      {showEditModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(8, 10, 15, 0.8)',
          backdropFilter: 'blur(6px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 999999,
          padding: 24,
        }}>
          <div style={{
            background: T.surface,
            border: `1px solid ${T.borderHi}`,
            borderRadius: 12,
            width: '100%',
            maxWidth: 500,
            maxHeight: '85vh',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            boxShadow: '0 12px 40px rgba(0, 0, 0, 0.7)'
          }}>
            {/* Modal Header */}
            <div style={{ padding: '16px 20px', borderBottom: `1px solid ${T.border}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: T.panelAlt }}>
              <span style={{ fontSize: 13, fontWeight: 700, color: '#fff', letterSpacing: '0.04em' }}>⚙️ MANAGE ACCOUNT BALANCE</span>
              <button onClick={() => setShowEditModal(false)} style={{ background: 'none', border: 'none', color: T.textDim, cursor: 'pointer', fontSize: 16 }}>×</button>
            </div>
            
            {/* Modal Body */}
            <div style={{ padding: 20, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
              {/* Cash Input */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <label style={{ fontSize: 9, fontWeight: 700, color: T.textMid }}>AVAILABLE CASH (₹)</label>
                <input 
                  type="number" 
                  value={tempCash} 
                  onChange={e => setTempCash(e.target.value)} 
                  style={{
                    background: T.bg, 
                    border: `1px solid ${T.border}`, 
                    borderRadius: 6, 
                    padding: '8px 12px', 
                    color: '#fff', 
                    fontSize: 12, 
                    fontFamily: "'IBM Plex Mono', monospace",
                    outline: 'none'
                  }}
                />
              </div>

              {/* Holdings List */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <label style={{ fontSize: 9, fontWeight: 700, color: T.textMid }}>STOCK HOLDINGS</label>
                <div style={{ border: `1px solid ${T.border}`, borderRadius: 6, background: T.panelAlt, overflow: 'hidden' }}>
                  {tempPortfolio.length === 0 ? (
                    <div style={{ padding: '12px 14px', fontSize: 11, color: T.textDim, textAlign: 'center' }}>No stock holdings. Add one below.</div>
                  ) : (
                    <div style={{ maxHeight: 150, overflowY: 'auto' }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11, textAlign: 'left' }}>
                        <thead>
                          <tr style={{ borderBottom: `1px solid ${T.border}`, color: T.textDim, fontSize: 9 }}>
                            <th style={{ padding: '6px 10px' }}>SYMBOL</th>
                            <th style={{ padding: '6px 10px' }}>SHARES</th>
                            <th style={{ padding: '6px 10px' }}>AVG COST</th>
                            <th style={{ padding: '6px 10px', textAlign: 'right' }}>ACTION</th>
                          </tr>
                        </thead>
                        <tbody>
                          {tempPortfolio.map((item, idx) => (
                            <tr key={item.symbol} style={{ borderBottom: idx < tempPortfolio.length - 1 ? `1px solid ${T.border}` : 'none', color: T.text }}>
                              <td style={{ padding: '8px 10px', fontWeight: 600 }}>{item.symbol.replace('.NS', '')}</td>
                              <td style={{ padding: '8px 10px' }}>
                                <input 
                                  type="number" 
                                  value={item.shares} 
                                  onChange={e => {
                                    const val = parseFloat(e.target.value);
                                    const updated = [...tempPortfolio];
                                    updated[idx].shares = isNaN(val) ? '' : val;
                                    setTempPortfolio(updated);
                                  }}
                                  style={{
                                    width: 70,
                                    background: T.bg,
                                    border: `1px solid ${T.border}`,
                                    borderRadius: 4,
                                    color: '#fff',
                                    fontSize: 10,
                                    padding: '2px 4px',
                                    fontFamily: "'IBM Plex Mono', monospace"
                                  }}
                                />
                              </td>
                              <td style={{ padding: '8px 10px' }}>
                                <input 
                                  type="number" 
                                  value={item.avgCost} 
                                  onChange={e => {
                                    const val = parseFloat(e.target.value);
                                    const updated = [...tempPortfolio];
                                    updated[idx].avgCost = isNaN(val) ? '' : val;
                                    setTempPortfolio(updated);
                                  }}
                                  style={{
                                    width: 80,
                                    background: T.bg,
                                    border: `1px solid ${T.border}`,
                                    borderRadius: 4,
                                    color: '#fff',
                                    fontSize: 10,
                                    padding: '2px 4px',
                                    fontFamily: "'IBM Plex Mono', monospace"
                                  }}
                                />
                              </td>
                              <td style={{ padding: '8px 10px', textAlign: 'right' }}>
                                <button 
                                  onClick={() => handleRemoveHolding(item.symbol)}
                                  style={{ background: 'none', border: 'none', color: T.red, cursor: 'pointer', fontSize: 10, fontWeight: 700 }}
                                >
                                  REMOVE
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>

              {/* Add Holding Form */}
              <div style={{ background: T.panel, border: `1px solid ${T.border}`, borderRadius: 8, padding: 12, display: 'flex', flexDirection: 'column', gap: 10 }}>
                <span style={{ fontSize: 9, fontWeight: 700, color: T.accentAlt }}>➕ ADD NEW STOCK POSITION</span>
                <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr 1fr', gap: 8 }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                    <label style={{ fontSize: 8, color: T.textMid }}>SYMBOL</label>
                    <select 
                      value={newHoldingSymbol} 
                      onChange={e => setNewHoldingSymbol(e.target.value)}
                      style={{
                        background: T.bg,
                        border: `1px solid ${T.border}`,
                        borderRadius: 6,
                        color: '#fff',
                        fontSize: 11,
                        padding: '6px 8px',
                        outline: 'none'
                      }}
                    >
                      {DEFAULT_WATCHLIST.map(w => (
                        <option key={w.symbol} value={w.symbol}>{w.symbol.replace('.NS', '')}</option>
                      ))}
                    </select>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                    <label style={{ fontSize: 8, color: T.textMid }}>SHARES</label>
                    <input 
                      type="number" 
                      placeholder="e.g. 10" 
                      value={newHoldingShares} 
                      onChange={e => setNewHoldingShares(e.target.value)}
                      style={{
                        background: T.bg,
                        border: `1px solid ${T.border}`,
                        borderRadius: 6,
                        color: '#fff',
                        fontSize: 11,
                        padding: '6px 8px',
                        fontFamily: "'IBM Plex Mono', monospace",
                        outline: 'none'
                      }}
                    />
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                    <label style={{ fontSize: 8, color: T.textMid }}>AVG COST (₹)</label>
                    <input 
                      type="number" 
                      placeholder="e.g. 2750" 
                      value={newHoldingAvgCost} 
                      onChange={e => setNewHoldingAvgCost(e.target.value)}
                      style={{
                        background: T.bg,
                        border: `1px solid ${T.border}`,
                        borderRadius: 6,
                        color: '#fff',
                        fontSize: 11,
                        padding: '6px 8px',
                        fontFamily: "'IBM Plex Mono', monospace",
                        outline: 'none'
                      }}
                    />
                  </div>
                </div>
                <button 
                  onClick={handleAddHolding}
                  style={{
                    background: 'rgba(0, 229, 168, 0.08)',
                    border: `1px solid ${T.green}40`,
                    borderRadius: 6,
                    padding: '6px 0',
                    color: T.green,
                    fontSize: 10,
                    fontWeight: 700,
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    marginTop: 4
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = 'rgba(0, 229, 168, 0.15)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'rgba(0, 229, 168, 0.08)'}
                >
                  ADD TO PORTFOLIO
                </button>
              </div>
            </div>
            
            {/* Modal Footer */}
            <div style={{ padding: '12px 20px', borderTop: `1px solid ${T.border}`, display: 'flex', justifyContent: 'flex-end', gap: 10, background: T.panelAlt }}>
              <button 
                onClick={() => setShowEditModal(false)}
                style={{
                  background: 'transparent',
                  border: `1px solid ${T.borderHi}`,
                  borderRadius: 6,
                  padding: '6px 14px',
                  color: T.textMid,
                  fontSize: 10,
                  fontWeight: 700,
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
                onMouseEnter={e => e.currentTarget.style.borderColor = T.textDim}
                onMouseLeave={e => e.currentTarget.style.borderColor = T.borderHi}
              >
                CANCEL
              </button>
              <button 
                onClick={handleSaveBalances}
                style={{
                  background: T.accent,
                  border: 'none',
                  borderRadius: 6,
                  padding: '6px 14px',
                  color: '#fff',
                  fontSize: 10,
                  fontWeight: 700,
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
                onMouseEnter={e => e.currentTarget.style.background = '#6c5ce7'}
                onMouseLeave={e => e.currentTarget.style.background = T.accent}
              >
                SAVE CHANGES
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
