import { apiFetch, deletePrediction } from './api';
import { formatError } from './utils/formatError';
import { getConfidenceScore } from './utils/performance';
import React, { useState, useEffect, useCallback } from 'react';
import { T, mono } from './theme';

const fmt = (n, d = 2) => n == null ? '—' : Number(n).toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d });

const WATCHLIST = [
  'YESBANK.NS', 'TATASTEEL.NS', 'BANKBARODA.NS', 'TATAPOWER.NS', 'SBIN.NS'
];

export default function PredictionsPanel({ prices = {}, selectedSymbol = 'YESBANK.NS', onSelectSymbol, onViewChange }) {
  const [predictions, setPredictions] = useState([]);
  const [stats, setStats] = useState({
    total_predictions: 0,
    resolved_predictions: 0,
    win_rate: 0.0,
    avg_error: 0.0,
    profit_factor: 0.0,
    empirical_rr_ratio: 0.0,
    expected_value_pct: 0.0,
    max_drawdown_pct: 0.0,
    best_sector: 'N/A',
    worst_sector: 'N/A',
    recent_outcomes: [],
    avg_confidence: 0.0,
    leaderboard: []
  });

  const [filter, setFilter] = useState('ALL'); // 'ALL', 'PENDING', 'RESOLVED'
  const [loading, setLoading] = useState(false);
  const [globalConfidence, setGlobalConfidence] = useState(null);
  const [dataConfidence, setDataConfidence] = useState(null);
  const [resolvingId, setResolvingId] = useState(null);
  const [actualOutcomeInput, setActualOutcomeInput] = useState('');

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
      const res = await apiFetch('/api/predictions');
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
      const res = await apiFetch('/api/predictions/stats');
      if (res.ok) {
        const data = await res.json();
        setStats(prev => ({ ...prev, ...data }));
      }
    } catch (err) {
      console.error("Error fetching stats:", err);
    }
  }, []);

  const fetchDataConfidence = useCallback(async (sym) => {
    try {
      const url = sym ? `/api/data/confidence?symbols=${encodeURIComponent(sym)}` : `/api/data/confidence`;
      const res = await apiFetch(url);
      if (res.ok) {
        const data = await res.json();
        const score = getConfidenceScore(data);
        setDataConfidence(score);
        setGlobalConfidence({ ...data, confidence_score: score });
      }
    } catch (err) {
      console.error("Error fetching data confidence:", err);
    }
  }, []);

  useEffect(() => {
    fetchPredictions();
    fetchStats();
  }, [fetchPredictions, fetchStats]);

  useEffect(() => {
    fetchDataConfidence(symbol);
  }, [symbol, fetchDataConfidence]);

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
      const res = await apiFetch('/api/predictions', {
        method: 'POST',
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
        setSubmitError(formatError(data.detail || data, "Failed to record prediction."));
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
      const res = await apiFetch(`/api/predictions/${resolvingId}/resolve`, {
        method: 'POST',
        body: JSON.stringify({
          exit_price: parseFloat(actualOutcomeInput)
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
      const res = await deletePrediction(predId);
      if (res.ok) {
        fetchPredictions();
        fetchStats();
      } else {
        console.error(`Failed to delete prediction ${predId}: HTTP ${res.status}`);
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
          <h2 style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.02em', color: '#fff', marginBottom: 4 }}> PREDICTION TRACKING CENTER</h2>
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

      {globalConfidence?.locked && (
        <div style={{ background: T.redDim, border: `1px solid ${T.red}`, padding: 12, borderRadius: 8, marginTop: 4, display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 18 }}>⚠</span>
          <div>
            <div style={{ color: T.red, fontWeight: 700, fontSize: 12, letterSpacing: '0.04em' }}>DATA INTEGRITY COMPROMISED</div>
            <div style={{ color: T.text, fontSize: 11, opacity: 0.9 }}>Database Data Confidence Score is {(globalConfidence.confidence_score ?? 0).toFixed(1)}% (Below 90% threshold). Analytics have been locked to prevent decision making on corrupted historical data.</div>
          </div>
        </div>
      )}

      {/* Metrics Widgets Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16, filter: globalConfidence?.locked ? 'blur(4px)' : 'none', pointerEvents: globalConfidence?.locked ? 'none' : 'auto', transition: 'all 0.3s ease' }}>
        
        {/* Metric 1: Win Rate */}
        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 10, padding: 16, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.08em', color: T.textMid, marginBottom: 4 }}>QUANT WIN RATE</div>
            <div style={{ fontSize: 28, fontWeight: 800, color: stats.win_rate >= 50 ? T.green : T.red, letterSpacing: '-0.03em', ...mono }}>
              {(stats.win_rate ?? 0).toFixed(1)}%
            </div>
          </div>
          <div style={{ fontSize: 10, color: T.textDim, borderTop: `1px solid ${T.border}`, paddingTop: 10, marginTop: 10 }}>
            Resolved: <strong style={{ color: T.text }}>{stats.resolved_predictions}</strong> / Total: <strong style={{ color: T.text }}>{stats.total_predictions}</strong>
          </div>
        </div>

        {/* Metric 2: Profit Factor */}
        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 10, padding: 16, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.08em', color: T.textMid, marginBottom: 4 }}>PROFIT FACTOR</div>
            <div style={{ fontSize: 28, fontWeight: 800, color: stats.profit_factor >= 1.5 ? T.green : stats.profit_factor >= 1.0 ? '#fbbf24' : T.red, letterSpacing: '-0.02em', ...mono }}>
              {(stats.profit_factor ?? 0).toFixed(2)}x
            </div>
          </div>
          <div style={{ fontSize: 10, color: T.textDim, borderTop: `1px solid ${T.border}`, paddingTop: 10, marginTop: 10 }}>
            Gross Profit / Gross Loss (Ideal &gt; 1.5x)
          </div>
        </div>

        {/* Metric 3: Expected Value (EV) */}
        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 10, padding: 16, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.08em', color: T.textMid, marginBottom: 4 }}>EXPECTED VALUE (EV)</div>
            <div style={{ fontSize: 24, fontWeight: 800, color: stats.expected_value_pct > 0 ? T.green : T.red, letterSpacing: '-0.02em', ...mono }}>
              {(stats.expected_value_pct ?? 0) > 0 ? '+' : ''}{(stats.expected_value_pct ?? 0).toFixed(2)}%
            </div>
          </div>
          <div style={{ fontSize: 10, color: T.textDim, borderTop: `1px solid ${T.border}`, paddingTop: 10, marginTop: 10 }}>
            Average expected return per trade
          </div>
        </div>

        {/* Metric 4: Max Drawdown */}
        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 10, padding: 16, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.08em', color: T.textMid, marginBottom: 4 }}>MAX DRAWDOWN</div>
            <div style={{ fontSize: 24, fontWeight: 800, color: stats.max_drawdown_pct <= 10 ? T.green : T.red, letterSpacing: '-0.02em', ...mono }}>
              -{(stats.max_drawdown_pct ?? 0).toFixed(2)}%
            </div>
          </div>
          <div style={{ fontSize: 10, color: T.textDim, borderTop: `1px solid ${T.border}`, paddingTop: 10, marginTop: 10 }}>
            Largest peak-to-trough capital drop
          </div>
        </div>

        {/* Metric 5: Empirical R */}
        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 10, padding: 16, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: '0.08em', color: T.textMid, marginBottom: 4 }}>REALIZED R-MULTIPLE</div>
            <div style={{ fontSize: 24, fontWeight: 800, color: stats.empirical_rr_ratio >= 1.5 ? T.green : '#fbbf24', letterSpacing: '-0.02em', ...mono }}>
              {(stats.empirical_rr_ratio ?? 0).toFixed(2)}R
            </div>
          </div>
          <div style={{ fontSize: 10, color: T.textDim, borderTop: `1px solid ${T.border}`, paddingTop: 10, marginTop: 10 }}>
            Actual Average Win / Average Loss
          </div>
        </div>

        {/* Metric 6: Confidence & Outcomes */}
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
            <span style={{ color: '#fff', fontWeight: 600 }}>{(stats.avg_confidence ?? 0).toFixed(0)}%</span>
          </div>
        </div>

      </div>

      {/* STRATEGY LEADERBOARD */}
      <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 12, padding: 20, filter: globalConfidence?.locked ? 'blur(4px)' : 'none', pointerEvents: globalConfidence?.locked ? 'none' : 'auto', transition: 'all 0.3s ease' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, borderBottom: `1px solid ${T.border}`, paddingBottom: 10 }}>
          <h3 style={{ fontSize: 13, fontWeight: 700, letterSpacing: '0.04em', color: '#fff', margin: 0 }}>
             SETUP LEADERBOARD (LIVE PERFORMANCE)
          </h3>
          {dataConfidence !== null && (
            <div style={{ background: T.panel, padding: '4px 10px', borderRadius: 6, border: `1px solid ${T.borderHi}`, fontSize: 11, ...mono, color: dataConfidence >= 72 ? T.green : T.red }}>
              Data Confidence ({symbol}): {(dataConfidence ?? 0).toFixed(1)}%
            </div>
          )}
        </div>
        <div style={{ overflowX: 'auto' }}>
          <div style={{ minWidth: '700px' }}>
            {/* Header */}
            <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr 1fr 1fr 1fr', padding: '8px 12px', borderBottom: `1px solid ${T.border}`, fontSize: 9, color: T.textMid, letterSpacing: '0.08em', ...mono }}>
              <span>SETUP TYPE</span>
              <span>WIN RATE</span>
              <span>PROFIT FACTOR</span>
              <span>EXPECTED VALUE</span>
              <span>STATUS</span>
            </div>
            
            {/* Rows */}
            {stats.leaderboard && stats.leaderboard.length > 0 ? (
              stats.leaderboard.map((item, idx) => {
                const isActive = item.profit_factor >= 1.0;
                return (
                  <div key={idx} style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr 1fr 1fr 1fr', padding: '12px 12px', borderBottom: `1px solid ${T.border}`, fontSize: 11, ...mono, alignItems: 'center' }}>
                    <span style={{ color: T.text, fontWeight: 700 }}>{item.setup_type}</span>
                    <span style={{ color: (item.win_rate ?? 0) >= 50 ? T.green : T.textMid }}>{(item.win_rate ?? 0).toFixed(1)}% ({item.wins}/{item.trades})</span>
                    <span style={{ color: (item.profit_factor ?? 0) >= 1.5 ? T.green : (item.profit_factor ?? 0) >= 1.0 ? '#fbbf24' : T.red, fontWeight: 700 }}>{(item.profit_factor ?? 0).toFixed(2)}x</span>
                    <span style={{ color: (item.ev_pct ?? 0) > 0 ? T.green : T.red }}>{(item.ev_pct ?? 0) > 0 ? '+' : ''}{(item.ev_pct ?? 0).toFixed(2)}%</span>
                    <span>
                      {isActive ? (
                        <span style={{ background: T.greenDim, color: T.green, padding: '2px 6px', borderRadius: 4, fontSize: 8, fontWeight: 700, border: `1px solid ${T.green}30` }}>ACTIVE</span>
                      ) : (
                        <span style={{ background: T.redDim, color: T.red, padding: '2px 6px', borderRadius: 4, fontSize: 8, fontWeight: 700, border: `1px solid ${T.red}30` }}>QUARANTINED (PF &lt; 1.0)</span>
                      )}
                    </span>
                  </div>
                );
              })
            ) : (
              <div style={{ padding: '20px 0', textAlign: 'center', color: T.textDim, fontSize: 11, ...mono }}>No setups recorded yet. Ensure trades are tagged with setup_type.</div>
            )}
          </div>
        </div>
      </div>

      {/* Main UI Layout: Form on left/top, History on right/bottom */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 24, alignItems: 'start' }}>
        
        {/* Card: Log Prediction Form */}
        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 12, padding: 20 }}>
          <h3 style={{ fontSize: 13, fontWeight: 700, letterSpacing: '0.04em', color: '#fff', marginBottom: 16, borderBottom: `1px solid ${T.border}`, paddingBottom: 10 }}>
             RECORD NEW SYSTEM PREDICTION
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
                <span style={{ color: '#fbbf24', ...mono }}>{confidence}%</span>
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
              onMouseEnter={e => { if(!loading) e.currentTarget.style.background = '#d97706'; }}
              onMouseLeave={e => { if(!loading) e.currentTarget.style.background = T.accent; }}
            >
              {loading ? "RECORDING..." : " SAVE SYSTEM PREDICTION"}
            </button>
          </form>
        </div>

        {/* Card: History Logs List */}
        <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 12, padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
          
          {/* Header & Filter switchers */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: `1px solid ${T.border}`, paddingBottom: 10 }}>
            <h3 style={{ fontSize: 13, fontWeight: 700, letterSpacing: '0.04em', color: '#fff' }}>
               PREDICTIONS LOG
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
                            background: isPending ? T.border : isCorrect ? T.greenDim : pred.status === 'FLAT' ? 'rgba(245, 158, 11, 0.12)' : T.redDim,
                            color: isPending ? T.textMid : isCorrect ? T.green : pred.status === 'FLAT' ? T.blue : T.red,
                            border: `1px solid ${isPending ? T.borderHi : isCorrect ? T.green : pred.status === 'FLAT' ? T.blue : T.red}30`
                          }}
                        >
                          {pred.status}
                        </span>
                        
                        <button
                          onClick={() => handleDelete(pred.id)}
                          title="Delete prediction"
                          aria-label={`Delete prediction for ${pred.symbol}`}
                          style={{
                            background: 'none',
                            border: 'none',
                            color: T.textDim,
                            cursor: 'pointer',
                            fontSize: 11,
                            padding: 2
                          }}
                          onMouseEnter={e => e.currentTarget.style.color = T.red}
                          onMouseLeave={e => e.currentTarget.style.color = T.textDim}
                        >
                          ✕
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
                    {(pred.rsi || pred.macd || pred.adx || pred.trade_quality_score) && (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 9, color: T.textMid, ...mono }}>
                        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                          {pred.rsi && <span>RSI: <strong style={{ color: T.text }}>{pred.rsi}</strong></span>}
                          {pred.macd && <span>MACD Hist: <strong style={{ color: T.text }}>{pred.macd}</strong></span>}
                          {pred.adx && <span>ADX: <strong style={{ color: T.text }}>{pred.adx}</strong></span>}
                          <span>Confidence: <strong style={{ color: '#fbbf24' }}>{pred.confidence_score}%</strong></span>
                        </div>
                        
                        {/* Phase Omega: Trade Quality Engine */}
                        {pred.trade_quality_score > 0 && (
                          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', padding: '6px', background: 'rgba(0,0,0,0.2)', borderRadius: '4px', border: `1px solid ${T.borderHi}` }}>
                            <span style={{ color: T.accent, fontWeight: 'bold' }}>TQS: {pred.trade_quality_score}</span>
                            <span>| Regime: {pred.regime_score}</span>
                            <span>| Sector: {pred.sector_score}</span>
                            <span>| RS: {pred.rs_score}</span>
                            <span>| Correl: {pred.correlation_score}</span>
                          </div>
                        )}
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
                              background: 'rgba(245, 158, 11, 0.08)',
                              border: `1px solid ${T.accent}30`,
                              borderRadius: 5,
                              color: T.accent,
                              fontSize: 9,
                              fontWeight: 700,
                              cursor: 'pointer',
                              transition: 'all 0.2s',
                              letterSpacing: '0.04em'
                            }}
                            onMouseEnter={e => e.currentTarget.style.background = 'rgba(245, 158, 11, 0.15)'}
                            onMouseLeave={e => e.currentTarget.style.background = 'rgba(245, 158, 11, 0.08)'}
                          >
                             MANUALLY RESOLVE PREDICTION
                          </button>
                        )}
                      </div>
                    ) : (
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, ...mono, borderTop: `1px solid ${T.border}`, paddingTop: 6, color: T.textMid }}>
                        <span>Simulated Exit (manual):</span>
                        <span style={{ color: pred.actual_outcome == null ? T.textMid : (isCorrect ? T.green : pred.status === 'FLAT' ? T.blue : T.red), fontWeight: 700 }}>
                          {pred.actual_outcome != null ? `₹${fmt(pred.actual_outcome, 1)}` : '—'}
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
