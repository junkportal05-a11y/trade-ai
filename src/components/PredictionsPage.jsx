import React, { useState } from 'react';

export function PredictionsPage() {
  const [symbol, setSymbol] = useState('RELIANCE');
  const [timeframe, setTimeframe] = useState('15m');
  const [bias, setBias] = useState('BULLISH');
  const [entry, setEntry] = useState('');
  const [target, setTarget] = useState('');
  const [stop, setStop] = useState('');
  const [confidence, setConfidence] = useState('72');
  const [rsi, setRsi] = useState('');
  const [macd, setMacd] = useState('');
  const [adx, setAdx] = useState '';
  const [thesis, setThesis] = useState '';

  const predictedAcc = 0.0;
  const resolvedCount = 0;
  const totalCount = 0;

  const strategies = ['Trend Scalper', 'Mean Reversion', 'Breakout Volume', 'RSI Scalper', 'Swing Trend Follower'];

  const handleAnalyzePredict = () => {
    // Analyze and produce a prediction result
    // In a real implementation, this would call the prediction engine
    console.log('ANALYZE & PREDICT:', { symbol, timeframe, bias, entry, target, stop });
  };

  const handleSavePrediction = () => {
    // Save the prediction to the tracking log
    console.log('SAVE SYSTEM PREDICTION:', { symbol, bias, entry, target, stop, confidence, rsi, macd, adx, thesis });
  };

  return (
    <div className="p-6 bg-[#0c0a09] min-h-screen">
      <h2 className="text-2xl font-bold text-white mb-4">Predictions</h2>
      <p className="text-slate-400">
        AI prediction engine with tracking log. Record predictions, track resolution,
        and view historical accuracy — all synthetic data labeled as such.
      </p>

      {/* Two-column row: AI Prediction Engine | Prediction Accuracy */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Left: AI Prediction Engine */}
        <section className="glass-panel rounded-2xl p-6">
          <h4 className="text-[11px] font-bold text-uppercase text-slate-500 mb-3">AI Prediction Engine</h4>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <p className="text-[10px] text-slate-500">Symbol</p>
              <input
                type="text"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                className="form-input"
                placeholder="RELIANCE"
              />
            </div>
            <div>
              <p className="text-[10px] text-slate-500">Timeframe</p>
              <select
                value={timeframe}
                onChange={(e) => setTimeframe(e.target.value)}
                className="form-input"
              >
                <option value="1m">1m</option>
                <option value="5m">5m</option>
                <option value="15m" selected>
                  15m
                </option>
                <option value="1D">1D</option>
              </select>
            </div>
          </div>
          <button
            className="btn-accent w-full mt-4 text-[11px] py-2"
            onClick={handleAnalyzePredict}
          >
            ANALYZE & PREDICT
          </button>
        </section>

        {/* Right: Prediction Accuracy */}
        <section className="glass-panel rounded-2xl p-6">
          <h4 className="text-[11px] font-bold text-uppercase text-slate-500 mb-3">Prediction Accuracy</h4>
          <div className="text-center mb-4">
            <div className="text-5xl font-bold text-white">{predictedAcc}%</div>
            <div className="text-[11px] text-slate-400">0 of 0 resolved</div>
          </div>
          <p className="text-[11px] text-slate-400">
            Accuracy updates as predictions resolve. The resolver worker records
            right/wrong for every prediction and updates accuracy per strategy.
          </p>
          <p className="text-[10px] text-slate-500">
            Currently: No resolved predictions — accuracy stays at 0.0%.
          </p>
        </section>
      </div>

      {/* Tracking Center card - Medium glass */}
      <section className="glass-panel rounded-2xl p-6">
        <h4 className="text-[11px] font-bold text-uppercase text-slate-500 mb-3">
          Prediction Tracking Center · Record a prediction
        </h4>

        {/* Form fields */}
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <p className="text-[10px] text-slate-500">Symbol</p>
            <input
              type="text"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              className="form-input"
              placeholder="RELIANCE"
            />
          </div>
          <div>
            <p className="text-[10px] text-slate-500">BULLISH / BEARISH</p>
            <div className="flex gap-2">
              <button
                className={`btn-ghost-bg text-[10px] font-medium rounded px-3 py-1 ${
                  bias === 'BULLISH' ? 'bg-white/20' : ''
                }`}
                onClick={() => setBias('BULLISH')}
              >
                BULLISH
              </button>
              <button
                className={`btn-ghost-bg text-[10px] font-medium rounded px-3 py-1 ${
                  bias === 'BEARISH' ? 'bg-white/20' : ''
                }`}
                onClick={() => setBias('BEARISH')}
              >
                BEARISH
              </button>
            </div>
          </div>
          <div>
            <p className="text-[10px] text-slate-500">Entry</p>
            <input
              type="number"
              value={entry}
              onChange={(e) => setEntry(e.target.value)}
              className="form-input"
              placeholder="e.g. 2450.50"
            />
          </div>
          <div>
            <p className="text-[10px] text-slate-500">Target</p>
            <input
              type="number"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              className="form-input"
              placeholder="e.g. 2500.00"
            />
          </div>
          <div>
            <p className="text-[10px] text-slate-500">Stop</p>
            <input
              type="number"
              value={stop}
              onChange={(e) => setStop(e.target.value)}
              className="form-input"
              placeholder="e.g. 2400.00"
            />
          </div>
          <div>
            <p className="text-[10px] text-slate-500">Confidence</p>
            <input
              type="number"
              value={confidence}
              onChange={(e) => setConfidence(e.target.value)}
              className="form-input"
              placeholder="72"
              min="1"
              max="100"
            />
          </div>
          <div>
            <p className="text-[10px] text-slate-500">RSI</p>
            <input
              type="number"
              value={rsi}
              onChange={(e) => setRsi(e.target.value)}
              className="form-input"
              placeholder="58"
            />
          </div>
          <div>
            <p className="text-[10px] text-slate-500">MACD</p>
            <input
              type="text"
              value={macd}
              onChange={(e) => setMacd(e.target.value)}
              className="form-input"
              placeholder="12,26,9"
            />
          </div>
          <div>
            <p className="text-[10px] text-slate-500">ADX</p>
            <input
              type="number"
              value={adx}
              onChange={(e) => setAdx(e.target.value)}
              className="form-input"
              placeholder="25"
            />
          </div>
          <div>
            <p className="text-[10px] text-slate-500">Thesis</p>
            <textarea
              rows={2}
              value={thesis}
              onChange={(e) => setThesis(e.target.value)}
              className="form-input w-full h-24 text-[10px] text-slate-400"
              placeholder="Brief thesis for the prediction..."
            ></textarea>
          </div>
        </div>

        {/* SAVE SYSTEM PREDICTION ghost button */}
        <button
          className="ghost-btn w-full mt-4 text-[11px] py-2"
          onClick={handleSavePrediction}
        >
          SAVE SYSTEM PREDICTION
        </button>
      </section>

      {/* Prediction log - empty state */}
      <section className="glass-panel rounded-2xl p-6 mt-6">
        <h4 className="text-[11px] font-bold text-uppercase text-slate-500 mb-3">
          Prediction log
        </h4>
        <p className="empty-state text-[11px]">No predictions recorded yet.</p>
        <p className="text-[10px] text-slate-400">
          Record predictions using the form above. The prediction resolver will
          record right/wrong outcomes and update accuracy per strategy.
        </p>
      </section>
    </div>
  );
}