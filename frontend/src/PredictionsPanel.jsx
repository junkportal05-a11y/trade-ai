import React, { useState, useEffect, useCallback } from 'react';

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
  greenGlow:  'rgba(0,229,168,0.3)',
  red:        '#ff3d5a',
  redDim:     'rgba(255,61,90,0.1)',
  redGlow:    'rgba(255,61,90,0.3)',
  gold:       '#f5c842',
  goldDim:    'rgba(245,200,66,0.1)',
  blue:       '#4da6ff',
  blueDim:    'rgba(77,166,255,0.1)',
  accent:     '#7b6cff',
  accentAlt:  '#9b5de5',
  accentDim:  'rgba(123,108,255,0.12)',
};

const mono = { fontFamily: "'IBM Plex Mono', monospace" };
const fmt = (n, d = 2) => n == null ? '—' : Number(n).toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d });

const WATCHLIST = [
  'HAL.NS', 'BEL.NS', 'RVNL.NS', 'IREDA.NS', 'HUDCO.NS',
  'COALINDIA.NS', 'NHPC.NS', 'ADANIPORTS.NS', 'TATAPOWER.NS', 'BHEL.NS',
  'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS',
  'SBIN.NS', 'TATAMOTORS.NS', 'BHARTIARTL.NS', 'ITC.NS', 'LT.NS',
  'ADANIENT.NS', 'ADANIPOWER.NS', 'IRFC.NS', 'PFC.NS', 'REC.NS',
  'ZOMATO.NS', 'TATASTEEL.NS', 'SAIL.NS', 'WIPRO.NS', 'JIOFIN.NS',
  'SJVN.NS', 'GMRINFRA.NS', 'NBCC.NS', 'JINDALSTEL.NS', 'JSWSTEEL.NS',
  'HINDALCO.NS', 'BPCL.NS', 'IOC.NS', 'ONGC.NS', 'NTPC.NS'
];

export default function PredictionsPanel({ prices = {}, selectedSymbol = 'HAL.NS', onSelectSymbol, onViewChange }) {
  const [predictions, setPredictions] = useState([]);
  const [stats, setStats] = useState({
    total_predictions: 0,
    resolved_predictions: 0,
    win_rate: 0.0,
    avg_error: 0.0,
    best_sector: 'N/A',
    worst_sector: 'N/A',
    recent_outcomes: [],
    avg_confidence: 0.0
  });

  const [filter, setFilter] = useState('ALL'); // 'ALL', 'PENDING', 'RESOLVED'
  const [loading, setLoading] = useState(false);
  const [resolvingId, setResolvingId] = useState(null);
  const [actualOutcomeInput, setActualOutcomeInput] = useState('');
  const [resolutionStatus, setResolutionStatus] = useState('CORRECT'); // 'CORRECT', 'INCORRECT', 'FLAT'

  // Form State
  const [symbol, setSymbol] = useState(selectedSymbol);
  const [predType, setPredType] = useState('UP'); // 'UP' or 'DOWN'
  const [entryPrice, setEntryPrice] = useState('');
  const [targetPrice, setTargetPrice] = useState('');
  const [stopLoss, setStopLoss] = useState('');
  const [confidence, setConfidence] = useState(80);
  const [rsi, setRsi] = useState('');
  const [macd, setMacd] = useState('');
  const [adx, setAdx] = useState('');
  const [reason, setReason] = useState('');
  const [submitError, setSubmitError] = useState('');
  const [submitSuccess, setSubmitSuccess] = useState('');

  // Fetch functions
  const fetchPredictions = useCallback(async () => {
    try {
      const res = await fetch(`${BASE}/api/predictions`, {
        credentials: 'include',
        headers: {}
      });
      if (res.ok) {
        const data = await res.json();
        setPredictions(data);
      }
    } catch (err) {
      console.error("Error fetching predictions:", err);
    }
  }, []);

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${BASE}/api/predictions/stats`, {
        credentials: 'include',
        headers: {}
      });
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (err) {
      console.error("Error fetching stats:", err);
    }
  }, []);

  useEffect(() => {
    fetchPredictions();
    fetchStats();
  }, [fetchPredictions, fetchStats]);

  // Handle selectedSymbol prop change to prefill form
  useEffect(() => {
    if (selectedSymbol) {
      setSymbol(selectedSymbol);
      const livePrice = prices[selectedSymbol]?.price;
      if (livePrice) {
        setEntryPrice(livePrice.toString());
        // Auto-calculate reasonable initial target (e.g. +3% for UP, -3% for DOWN) and SL
        const priceVal = parseFloat(livePrice);
        if (predType === 'UP') {
          setTargetPrice((priceVal * 1.03).toFixed(2));
          setStopLoss((priceVal * 0.985).toFixed(2));
        } else {
          setTargetPrice((priceVal * 0.97).toFixed(2));
          setStopLoss((priceVal * 1.015).toFixed(2));
        }
      }
    }
  }, [selectedSymbol, prices, predType]);

  // Adjust target/stop-loss when symbol or type changes
  const handleSymbolChange = (newSym) => {
    setSymbol(newSym);
    const livePrice = prices[newSym]?.price;
    if (livePrice) {
      setEntryPrice(livePrice.toString());
      const priceVal = parseFloat(livePrice);
      if (predType === 'UP') {
        setTargetPrice((priceVal * 1.03).toFixed(2));
        setStopLoss((priceVal * 0.985).toFixed(2));
      } else {
        setTargetPrice((priceVal * 0.97).toFixed(2));
        setStopLoss((priceVal * 1.015).toFixed(2));
      }
    }
  };

  const handleTypeChange = (type) => {
    setPredType(type);
    const currEntry = parseFloat(entryPrice) || (prices[symbol]?.price) || 0;
    if (currEntry > 0) {
      if (type === 'UP') {
        setTargetPrice((currEntry * 1.03).toFixed(2));
        setStopLoss((currEntry * 0.985).toFixed(2));
      } else {
        setTargetPrice((currEntry * 0.97).toFixed(2));
        setStopLoss((currEntry * 1.015).toFixed(2));
      }
    }
  };

  const prefillCurrentPrice = () => {
    const livePrice = prices[symbol]?.price;
    if (livePrice) {
      setEntryPrice(livePrice.toString());
      const priceVal = parseFloat(livePrice);
      if (predType === 'UP') {
        setTargetPrice((priceVal * 1.03).toFixed(2));
        setStopLoss((priceVal * 0.985).toFixed(2));
      } else {
        setTargetPrice((priceVal * 0.97).toFixed(2));
        setStopLoss((priceVal * 1.015).toFixed(2));
      }
    }
  };

  // Submit Prediction Record
  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitError('');
    setSubmitSuccess('');
    setLoading(true);

    if (!entryPrice || !targetPrice || !stopLoss) {
      setSubmitError("Entry, Target, and Stop Loss prices are required.");
      setLoading(false);
      return;
    }

    const payload = {
      symbol,
      prediction_type: predType,
      entry_price: parseFloat(entryPrice),
      target_price: parseFloat(targetPrice),
      stop_loss: parseFloat(stopLoss),
      confidence_score: parseInt(confidence),
      rsi: rsi ? parseFloat(rsi) : null,
      macd: macd ? parseFloat(macd) : null,
      adx: adx ? parseFloat(adx) : null,
      reason: reason
    };

    try {
      const res = await fetch(`${BASE}/api/predictions`, {
        credentials: 'include',
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        setSubmitSuccess("Prediction recorded successfully!");
        setReason('');
        setRsi('');
        setMacd('');
        setAdx('');
        fetchPredictions();
        fetchStats();
      } else {
        const data = await res.json();
        setSubmitError(data.detail || "Failed to record prediction.");
      }
    } catch (err) {
      setSubmitError("Network error. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  // Resolve Prediction
  const handleResolveSubmit = async (e) => {
    e.preventDefault();
    if (!actualOutcomeInput) return;
    try {
      const res = await fetch(`${BASE}/api/predictions/${resolvingId}/resolve`, {
        credentials: 'include',
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          actual_outcome: parseFloat(actualOutcomeInput),
          status: resolutionStatus
        })
      });

      if (res.ok) {
        setResolvingId(null);
        setActualOutcomeInput('');
        fetchPredictions();
        fetchStats();
      }
    } catch (err) {
      console.error("Failed to resolve prediction:", err);
    }
  };

  // Delete Prediction
  const handleDelete = async (predId) => {
    if (!window.confirm("Are you sure you want to delete this prediction?")) return;
    try {
      const res = await fetch(`${BASE}/api/predictions/${predId}`, {
        credentials: 'include',
        method: 'DELETE',
        headers: {}
      });
      if (res.ok) {
        fetchPredictions();
        fetchStats();
      }
    } catch (err) {
      console.error("Failed to delete prediction:", err);
    }
  };

  // Filtered predictions
  const filteredPredictions = predictions.filter(p => {
    if (filter === 'ALL') return true;
    if (filter === 'PENDING') return p.status === 'PENDING';
    if (filter === 'RESOLVED') return p.status !== 'PENDING';
    return true;
  });

  return (
    <div style={{ flex: 1, background: T.bg, padding: 24, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 24, boxSizing: 'border-box' }}>
      
      {/* Title */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: `1px solid ${T.border}`, paddingBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.02em', color: '#fff', marginBottom: 4 }}>🔮 PREDICTION TRACKING CENTER</h2>
          <p style={{ fontSize: 11, color: T.textMid }}>Validate trading thesis, compute win rate stats, and track indicator models.</p>
        </div>
        <button
          onClick={() => onViewChange('CHART')}
          style={{
            padding: '6px 12px',
            background: 'transparent',
            border: `1px solid ${T.border}`,
            borderRadius: 6,
            color: T.textMid,
            fontSize: 10,
            fontWeight: 700,
            cursor: 'pointer',
            transition: 'all 0.2s'
          }}
          onMouseEnter={e => e.currentTarget.style.color = '#fff'}
          onMouseLeave={e => e.currentTarget.style.color = T.textMid}
        >
          ← BACK TO CHARTS
        </button>
      </div>

      {/* Metrics Widgets Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 }}>
        
        {/* Metric 1: Win Rate */}
        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 10, padding: 16, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.08em', color: T.textMid, marginBottom: 4 }}>QUANT WIN RATE</div>
            <div style={{ fontSize: 28, fontWeight: 800, color: stats.win_rate >= 50 ? T.green : T.red, letterSpacing: '-0.03em', ...mono }}>
              {stats.win_rate.toFixed(1)}%
            </div>
          </div>
          <div style={{ fontSize: 10, color: T.textDim, borderTop: `1px solid ${T.border}`, paddingTop: 10, marginTop: 10 }}>
            Resolved: <strong style={{ color: T.text }}>{stats.resolved_predictions}</strong> / Total: <strong style={{ color: T.text }}>{stats.total_predictions}</strong>
          </div>
        </div>

        {/* Metric 2: Mean Absolute Error */}
        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 10, padding: 16, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.08em', color: T.textMid, marginBottom: 4 }}>MEAN ABSOLUTE ERROR</div>
            <div style={{ fontSize: 24, fontWeight: 800, color: T.blue, letterSpacing: '-0.02em', ...mono }}>
              ₹{fmt(stats.avg_error)}
            </div>
          </div>
          <div style={{ fontSize: 10, color: T.textDim, borderTop: `1px solid ${T.border}`, paddingTop: 10, marginTop: 10 }}>
            Average discrepancy to target level
          </div>
        </div>

        {/* Metric 3: Sector Breakdown */}
        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 10, padding: 16, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.08em', color: T.textMid, marginBottom: 8 }}>SECTOR ANALYTICS</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10 }}>
                <span style={{ color: T.textMid }}>Best Sector:</span>
                <span style={{ color: T.green, fontWeight: 700 }}>{stats.best_sector}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10 }}>
                <span style={{ color: T.textMid }}>Worst Sector:</span>
                <span style={{ color: T.red, fontWeight: 700 }}>{stats.worst_sector}</span>
              </div>
            </div>
          </div>
          <div style={{ fontSize: 10, color: T.textDim, borderTop: `1px solid ${T.border}`, paddingTop: 10, marginTop: 10 }}>
            Based on resolved Nifty categories
          </div>
        </div>

        {/* Metric 4: Confidence & Outcomes */}
        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 10, padding: 16, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.08em', color: T.textMid, marginBottom: 6 }}>RECENT OUTCOMES</div>
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 8 }}>
              {stats.recent_outcomes.length === 0 ? (
                <span style={{ fontSize: 9, color: T.textDim }}>No history available yet.</span>
              ) : (
                stats.recent_outcomes.map((win, idx) => (
                  <span
                    key={idx}
                    title={win ? "Correct" : "Incorrect"}
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: 2,
                      background: win ? T.green : T.red,
                      display: 'inline-block'
                    }}
                  />
                ))
              )}
            </div>
          </div>
          <div style={{ fontSize: 10, color: T.textDim, borderTop: `1px solid ${T.border}`, paddingTop: 10, marginTop: 6, display: 'flex', justifyContent: 'space-between' }}>
            <span>Avg Confidence:</span>
            <span style={{ color: '#fff', fontWeight: 600 }}>{stats.avg_confidence.toFixed(0)}%</span>
          </div>
        </div>

      </div>

      {/* Main UI Layout: Form on left/top, History on right/bottom */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 24, alignItems: 'start' }}>
        
        {/* Card: Log Prediction Form */}
        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 12, padding: 20 }}>
          <h3 style={{ fontSize: 13, fontWeight: 700, letterSpacing: '0.04em', color: '#fff', marginBottom: 16, borderBottom: `1px solid ${T.border}`, paddingBottom: 10 }}>
            🔮 RECORD NEW SYSTEM PREDICTION
          </h3>

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {/* Symbol & Direction Toggles */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div>
                <label style={{ fontSize: 10, fontWeight: 700, color: T.textMid, display: 'block', marginBottom: 6 }}>SYMBOL</label>
                <select
                  value={symbol}
                  onChange={(e) => handleSymbolChange(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    background: T.panel,
                    border: `1px solid ${T.border}`,
                    borderRadius: 6,
                    color: '#fff',
                    fontSize: 11,
                    outline: 'none'
                  }}
                >
                  {WATCHLIST.map(sym => (
                    <option key={sym} value={sym}>{sym.replace('.NS', '')}</option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ fontSize: 10, fontWeight: 700, color: T.textMid, display: 'block', marginBottom: 6 }}>BIAS DIRECTION</label>
                <div style={{ display: 'flex', gap: 6 }}>
                  <button
                    type="button"
                    onClick={() => handleTypeChange('UP')}
                    style={{
                      flex: 1,
                      padding: '7px 0',
                      borderRadius: 6,
                      border: `1px solid ${predType === 'UP' ? T.green : T.border}`,
                      background: predType === 'UP' ? T.greenDim : 'transparent',
                      color: predType === 'UP' ? T.green : T.textDim,
                      fontSize: 10,
                      fontWeight: 700,
                      cursor: 'pointer'
                    }}
                  >
                    ▲ BULLISH
                  </button>
                  <button
                    type="button"
                    onClick={() => handleTypeChange('DOWN')}
                    style={{
                      flex: 1,
                      padding: '7px 0',
                      borderRadius: 6,
                      border: `1px solid ${predType === 'DOWN' ? T.red : T.border}`,
                      background: predType === 'DOWN' ? T.redDim : 'transparent',
                      color: predType === 'DOWN' ? T.red : T.textDim,
                      fontSize: 10,
                      fontWeight: 700,
                      cursor: 'pointer'
                    }}
                  >
                    ▼ BEARISH
                  </button>
                </div>
              </div>
            </div>

            {/* Price Inputs */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <label style={{ fontSize: 9, fontWeight: 700, color: T.textMid }}>ENTRY</label>
                  <span onClick={prefillCurrentPrice} style={{ fontSize: 8, color: T.accent, cursor: 'pointer', textDecoration: 'underline' }}>LIVE</span>
                </div>
                <input
                  type="number"
                  step="0.05"
                  value={entryPrice}
                  onChange={(e) => setEntryPrice(e.target.value)}
                  placeholder="0.00"
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    background: T.panel,
                    border: `1px solid ${T.border}`,
                    borderRadius: 6,
                    color: '#fff',
                    fontSize: 11,
                    outline: 'none',
                    boxSizing: 'border-box',
                    ...mono
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: 9, fontWeight: 700, color: T.textMid, display: 'block', marginBottom: 6 }}>TARGET</label>
                <input
                  type="number"
                  step="0.05"
                  value={targetPrice}
                  onChange={(e) => setTargetPrice(e.target.value)}
                  placeholder="0.00"
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    background: T.panel,
                    border: `1px solid ${T.border}`,
                    borderRadius: 6,
                    color: '#fff',
                    fontSize: 11,
                    outline: 'none',
                    boxSizing: 'border-box',
                    ...mono
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: 9, fontWeight: 700, color: T.textMid, display: 'block', marginBottom: 6 }}>STOP LOSS</label>
                <input
                  type="number"
                  step="0.05"
                  value={stopLoss}
                  onChange={(e) => setStopLoss(e.target.value)}
                  placeholder="0.00"
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    background: T.panel,
                    border: `1px solid ${T.border}`,
                    borderRadius: 6,
                    color: '#fff',
                    fontSize: 11,
                    outline: 'none',
                    boxSizing: 'border-box',
                    ...mono
                  }}
                />
              </div>
            </div>

            {/* Confidence Slider */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, fontWeight: 700, color: T.textMid, marginBottom: 6 }}>
                <span>CONFIDENCE SCORE</span>
                <span style={{ color: T.gold, ...mono }}>{confidence}%</span>
              </div>
              <input
                type="range"
                min="10"
                max="100"
                step="5"
                value={confidence}
                onChange={(e) => setConfidence(e.target.value)}
                style={{ width: '100%', accentColor: T.accent, cursor: 'pointer' }}
              />
            </div>

            {/* Technical Indicators */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, background: T.panelAlt, border: `1px solid ${T.border}`, padding: '10px 12px', borderRadius: 8 }}>
              <div>
                <label style={{ fontSize: 9, fontWeight: 700, color: T.textDim, display: 'block', marginBottom: 4 }}>RSI (14)</label>
                <input
                  type="number"
                  step="0.1"
                  value={rsi}
                  onChange={(e) => setRsi(e.target.value)}
                  placeholder="e.g. 48.5"
                  style={{
                    width: '100%',
                    padding: '6px 8px',
                    background: T.panel,
                    border: `1px solid ${T.border}`,
                    borderRadius: 5,
                    color: '#fff',
                    fontSize: 10,
                    outline: 'none',
                    boxSizing: 'border-box',
                    ...mono
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: 9, fontWeight: 700, color: T.textDim, display: 'block', marginBottom: 4 }}>MACD HIST</label>
                <input
                  type="number"
                  step="0.05"
                  value={macd}
                  onChange={(e) => setMacd(e.target.value)}
                  placeholder="e.g. 1.25"
                  style={{
                    width: '100%',
                    padding: '6px 8px',
                    background: T.panel,
                    border: `1px solid ${T.border}`,
                    borderRadius: 5,
                    color: '#fff',
                    fontSize: 10,
                    outline: 'none',
                    boxSizing: 'border-box',
                    ...mono
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: 9, fontWeight: 700, color: T.textDim, display: 'block', marginBottom: 4 }}>ADX (14)</label>
                <input
                  type="number"
                  step="0.1"
                  value={adx}
                  onChange={(e) => setAdx(e.target.value)}
                  placeholder="e.g. 24.1"
                  style={{
                    width: '100%',
                    padding: '6px 8px',
                    background: T.panel,
                    border: `1px solid ${T.border}`,
                    borderRadius: 5,
                    color: '#fff',
                    fontSize: 10,
                    outline: 'none',
                    boxSizing: 'border-box',
                    ...mono
                  }}
                />
              </div>
            </div>

            {/* Reason Thesis Textarea */}
            <div>
              <label style={{ fontSize: 10, fontWeight: 700, color: T.textMid, display: 'block', marginBottom: 6 }}>THESIS REASONING</label>
              <textarea
                rows="2"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Technical trigger thesis, volume breakout patterns..."
                style={{
                  width: '100%',
                  padding: '8px 10px',
                  background: T.panel,
                  border: `1px solid ${T.border}`,
                  borderRadius: 6,
                  color: '#fff',
                  fontSize: 11,
                  fontFamily: "'Inter', sans-serif",
                  outline: 'none',
                  resize: 'none',
                  boxSizing: 'border-box'
                }}
              />
            </div>

            {submitError && <div style={{ fontSize: 11, color: T.red, fontWeight: 600 }}>✗ {submitError}</div>}
            {submitSuccess && <div style={{ fontSize: 11, color: T.green, fontWeight: 600 }}>✓ {submitSuccess}</div>}

            <button
              type="submit"
              disabled={loading}
              style={{
                marginTop: 6,
                padding: '10px 0',
                background: T.accent,
                border: 'none',
                borderRadius: 6,
                color: '#fff',
                fontSize: 11,
                fontWeight: 700,
                cursor: 'pointer',
                letterSpacing: '0.04em',
                transition: 'all 0.2s',
                opacity: loading ? 0.7 : 1
              }}
              onMouseEnter={e => { if(!loading) e.currentTarget.style.background = '#6c5ce7'; }}
              onMouseLeave={e => { if(!loading) e.currentTarget.style.background = T.accent; }}
            >
              {loading ? "RECORDING..." : "🔮 SAVE SYSTEM PREDICTION"}
            </button>
          </form>
        </div>

        {/* Card: History Logs List */}
        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 12, padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
          
          {/* Header & Filter switchers */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: `1px solid ${T.border}`, paddingBottom: 10 }}>
            <h3 style={{ fontSize: 13, fontWeight: 700, letterSpacing: '0.04em', color: '#fff' }}>
              📊 PREDICTIONS LOG
            </h3>
            
            <div style={{ display: 'flex', background: T.panel, borderRadius: 5, padding: 2, border: `1px solid ${T.border}` }}>
              {['ALL', 'PENDING', 'RESOLVED'].map(f => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  style={{
                    padding: '3px 8px',
                    borderRadius: 3,
                    border: 'none',
                    cursor: 'pointer',
                    background: filter === f ? T.borderHi : 'transparent',
                    color: filter === f ? '#fff' : T.textMid,
                    fontSize: 9,
                    fontWeight: 700
                  }}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>

          {/* Predictions Scroll Container */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12, maxHeight: 460, overflowY: 'auto', paddingRight: 4 }}>
            {filteredPredictions.length === 0 ? (
              <div style={{ fontSize: 11, color: T.textDim, padding: '24px 0', textAlign: 'center' }}>
                No predictions logged matching this filter.
              </div>
            ) : (
              filteredPredictions.map(pred => {
                const isPending = pred.status === 'PENDING';
                const isCorrect = pred.status === 'CORRECT';
                const isUp = pred.prediction_type === 'UP';

                // Status border coloring
                let statusBorder = T.border;
                if (!isPending) {
                  statusBorder = isCorrect ? `${T.green}40` : pred.status === 'FLAT' ? `${T.blue}40` : `${T.red}40`;
                }

                return (
                  <div
                    key={pred.id}
                    style={{
                      background: T.panelAlt,
                      border: `1px solid ${statusBorder}`,
                      borderRadius: 8,
                      padding: 12,
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 8,
                      position: 'relative'
                    }}
                  >
                    {/* Header: Date, Symbol, Status badge, and Delete */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span
                          onClick={() => {
                            if (onSelectSymbol) onSelectSymbol(pred.symbol);
                            if (onViewChange) onViewChange('CHART');
                          }}
                          style={{ fontSize: 12, fontWeight: 700, color: '#fff', cursor: 'pointer', textDecoration: 'underline' }}
                        >
                          {pred.symbol.replace('.NS', '')}
                        </span>
                        <span style={{ fontSize: 9, color: T.textDim }}>{pred.prediction_date}</span>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span
                          style={{
                            fontSize: 8,
                            fontWeight: 700,
                            padding: '2px 6px',
                            borderRadius: 4,
                            background: isPending ? T.border : isCorrect ? T.greenDim : pred.status === 'FLAT' ? T.blueDim : T.redDim,
                            color: isPending ? T.textMid : isCorrect ? T.green : pred.status === 'FLAT' ? T.blue : T.red,
                            border: `1px solid ${isPending ? T.borderHi : isCorrect ? T.green : pred.status === 'FLAT' ? T.blue : T.red}30`
                          }}
                        >
                          {pred.status}
                        </span>
                        
                        <button
                          onClick={() => handleDelete(pred.id)}
                          style={{
                            background: 'none',
                            border: 'none',
                            color: T.textDim,
                            cursor: 'pointer',
                            fontSize: 10,
                            padding: 2
                          }}
                          onMouseEnter={e => e.currentTarget.style.color = T.red}
                          onMouseLeave={e => e.currentTarget.style.color = T.textDim}
                        >
                          🗑️
                        </button>
                      </div>
                    </div>

                    {/* Prediction metrics: entry, target, stop loss */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, borderTop: `1px solid ${T.border}`, borderBottom: `1px solid ${T.border}`, padding: '6px 0', fontSize: 10, ...mono }}>
                      <div>
                        <span style={{ display: 'block', fontSize: 8, color: T.textDim }}>BIAS</span>
                        <span style={{ fontWeight: 700, color: isUp ? T.green : T.red }}>
                          {isUp ? '▲ BULLISH' : '▼ BEARISH'}
                        </span>
                      </div>
                      <div>
                        <span style={{ display: 'block', fontSize: 8, color: T.textDim }}>ENTRY</span>
                        <span style={{ color: T.text }}>₹{fmt(pred.entry_price, 1)}</span>
                      </div>
                      <div>
                        <span style={{ display: 'block', fontSize: 8, color: T.textDim }}>TARGET</span>
                        <span style={{ color: T.green }}>₹{fmt(pred.target_price, 1)}</span>
                      </div>
                      <div>
                        <span style={{ display: 'block', fontSize: 8, color: T.textDim }}>STOP LOSS</span>
                        <span style={{ color: T.red }}>₹{fmt(pred.stop_loss, 1)}</span>
                      </div>
                    </div>

                    {/* Indicators details */}
                    {(pred.rsi || pred.macd || pred.adx) && (
                      <div style={{ display: 'flex', gap: 12, fontSize: 9, color: T.textMid, ...mono }}>
                        {pred.rsi && <span>RSI: <strong style={{ color: T.text }}>{pred.rsi}</strong></span>}
                        {pred.macd && <span>MACD Hist: <strong style={{ color: T.text }}>{pred.macd}</strong></span>}
                        {pred.adx && <span>ADX: <strong style={{ color: T.text }}>{pred.adx}</strong></span>}
                        <span>Confidence: <strong style={{ color: T.gold }}>{pred.confidence_score}%</strong></span>
                      </div>
                    )}

                    {/* Thesis */}
                    {pred.reason && (
                      <div style={{ fontSize: 10.5, color: T.textMid, fontStyle: 'italic', lineHeight: 1.4, background: T.panel, padding: '6px 8px', borderRadius: 4 }}>
                        Thesis: {pred.reason}
                      </div>
                    )}

                    {/* Actual outcome exit if resolved, or resolve triggers if pending */}
                    {isPending ? (
                      <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
                        {resolvingId === pred.id ? (
                          <form onSubmit={handleResolveSubmit} style={{ display: 'flex', gap: 6, width: '100%', alignItems: 'center' }}>
                            <input
                              type="number"
                              step="0.05"
                              value={actualOutcomeInput}
                              onChange={(e) => setActualOutcomeInput(e.target.value)}
                              placeholder="Exit Price (₹)"
                              required
                              style={{
                                flex: 1,
                                padding: '5px 8px',
                                background: T.panel,
                                border: `1px solid ${T.border}`,
                                borderRadius: 4,
                                color: '#fff',
                                fontSize: 10,
                                outline: 'none',
                                boxSizing: 'border-box',
                                ...mono
                              }}
                            />
                            
                            <select
                              value={resolutionStatus}
                              onChange={(e) => setResolutionStatus(e.target.value)}
                              style={{
                                padding: '5px 8px',
                                background: T.panel,
                                border: `1px solid ${T.border}`,
                                borderRadius: 4,
                                color: '#fff',
                                fontSize: 9,
                                outline: 'none'
                              }}
                            >
                              <option value="CORRECT">CORRECT</option>
                              <option value="INCORRECT">INCORRECT</option>
                              <option value="FLAT">FLAT</option>
                            </select>

                            <button
                              type="submit"
                              style={{
                                padding: '5px 10px',
                                background: T.green,
                                border: 'none',
                                borderRadius: 4,
                                color: T.bg,
                                fontSize: 9,
                                fontWeight: 700,
                                cursor: 'pointer'
                              }}
                            >
                              SUBMIT
                            </button>
                            <button
                              type="button"
                              onClick={() => setResolvingId(null)}
                              style={{
                                padding: '5px 10px',
                                background: T.border,
                                border: `1px solid ${T.borderHi}`,
                                borderRadius: 4,
                                color: T.textMid,
                                fontSize: 9,
                                fontWeight: 700,
                                cursor: 'pointer'
                              }}
                            >
                              CANCEL
                            </button>
                          </form>
                        ) : (
                          <button
                            onClick={() => {
                              setResolvingId(pred.id);
                              // prefill exit with current price if available
                              const currentVal = prices[pred.symbol]?.price ?? pred.entry_price;
                              setActualOutcomeInput(currentVal.toString());
                            }}
                            style={{
                              width: '100%',
                              padding: '6px 0',
                              background: 'rgba(123, 108, 255, 0.08)',
                              border: `1px solid ${T.accent}30`,
                              borderRadius: 5,
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
                            ⚙️ MANUALLY RESOLVE PREDICTION
                          </button>
                        )}
                      </div>
                    ) : (
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, ...mono, borderTop: `1px solid ${T.border}`, paddingTop: 6, color: T.textMid }}>
                        <span>Resolved Price:</span>
                        <span style={{ color: isCorrect ? T.green : pred.status === 'FLAT' ? T.blue : T.red, fontWeight: 700 }}>
                          ₹{fmt(pred.actual_outcome, 1)}
                        </span>
                      </div>
                    )}

                  </div>
                );
              })
            )}
          </div>

        </div>

      </div>

    </div>
  );
}
