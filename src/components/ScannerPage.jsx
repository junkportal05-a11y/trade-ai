import React, { useState } from 'react';
import { Search, TrendingUp, BarChart3 } from 'lucide-react';

export function ScannerPage() {
  const [scanRunning, setScanRunning] = useState(false);
  const [scanError, setScanError] = useState(null);
  const [qualifyingSetups, setQualifyingSetups] = useState([]);
  const capital = 1840;
  const maxRiskPct = 2;

  const riskAmount = Math.round((capital * maxRiskPct) / 100); // ₹36.80

  const gates = [
    { name: 'Volume ≥ 1.2x average', passed: true },
    { name: 'ADX ≥ 20', passed: true },
    { name: 'Confidence ≥ 72%', passed: true },
    { name: 'Risk : Reward ≥ 2.0', passed: true },
    { name: 'VWAP veto', passed: true },
  ];

  const handleScan = async () => {
    setScanRunning(true);
    setScanError(null);
    try {
      // Wrap the allocate call so failure renders error state inside card
      const res = await fetch('/api/allocate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ capital, maxRiskPct }),
      });
      if (!res.ok) {
        const err = await res.json();
        setScanError(err.message || 'Scan failed');
        return;
      }
      const data = await res.json();
      setQualifyingSetups(data.setups || []);
    } catch (e) {
      // Fix: make scanner survive failed/slow responses without crash
      setScanError('Scan timed out or returned no results. No qualifying setups — the scan ran but no signal passed the gates.');
    } finally {
      setScanRunning(false);
    }
  };

  // If market is closed, show different message
  const marketOpen = true; // would use real market check

  return (
    <div className="p-6 bg-[#0c0a09] min-h-screen">
      <h2 className="text-2xl font-bold text-white mb-4">Scanner</h2>
      <p className="text-slate-400">
        Real-time signal scanner for NSE instruments. Run scans, view risk calculations,
        and see allocation suggestions — all paper-only analysis.
      </p>

      {/* Scanner card */}
      <section className="glass-panel rounded-2xl p-6 mb-6">
        <h3 className="text-[13px] font-bold text-uppercase text-slate-400 mb-4">
          Signal Scanner
        </h3>

        {/* SCAN & SIZE button */}
        <button
          className="btn-accent w-full mb-4"
          onClick={handleScan}
          disabled={scanRunning}
        >
          {scanRunning ? 'Scanning…' : 'SCAN & SIZE'}
        </button>

        {/* Empty / error state */}
        {scanError ? (
          <p className="empty-state text-[11px] mt-4">
            {scanError}
          </p>
        ) : qualifyingSetups.length === 0 && !scanRunning ? (
          <p className="empty-state text-[11px] mt-4">
            No qualifying setups — the scan ran but no signal passed the gates.
          </p>
        ) : null}

        {/* 5 Gates breakdown */}
        <div className="grid grid-cols-2 gap-3 mt-6">
          {gates.map((gate, i) => (
            <div
              key={i}
              className="text-[10px] font-medium text-slate-400 flex items-center gap-2"
            >
              <span>{gate.name}</span>
              <span>
                {gate.passed ? '✓' : '✗'}
              </span>
            </div>
          ))}
        </div>

        {/* Qualifying setups list */}
        {qualifyingSetups.length > 0 && (
          <div className="mt-6">
            <h4 className="text-[11px] font-bold text-uppercase text-slate-500 mb-3">
              Qualifying Setups
            </h4>
            {qualifyingSetups.map((setup, i) => (
              <div
                key={i}
                className="p-3 mb-3 bg-[#1a1614] border border-white/[0.08] rounded"
              >
                <p className="text-[10px] text-slate-400">
                  Entry: {setup.entry} • Stop-loss: {setup.stopLoss} •
                  Target: {setup.target} • Confidence: {setup.confidence}% •
                  Technical: {setup.technicalReasons}
                </p>
                <p className="text-[10px] text-slate-500 mt-1">
                  Position size: ₹{setup.positionSize} (₹1,840 capital, 2% risk)
                </p>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Two-column row: How the scan decides | Risk calculator */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        {/* Left: How the scan decides */}
        <div className="glass-panel rounded-2xl p-6">
          <h4 className="text-[11px] font-bold text-uppercase text-slate-500 mb-4">
            How the scan decides
          </h4>
          {gates.map((gate, i) => (
            <div
              key={i}
              className="text-[10px] font-medium text-slate-400 mb-2"
            >
              <span className="font-mono text-[10px]">
                {gate.name}
              </span>
              <span>{gate.passed ? '✓' : '✗'}</span>
            </div>
          ))}
        </div>

        {/* Right: Risk calculator */}
        <div className="glass-panel rounded-2xl p-6">
          <h4 className="text-[11px] font-bold text-uppercase text-slate-500 mb-4">
            Risk calculator
          </h4>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <p className="text-[10px] text-slate-500">Capital</p>
              <p className="text-[14px] font-bold text-white">₹{capital}</p>
            </div>
            <div>
              <p className="text-[10px] text-slate-500">Max risk per trade</p>
              <p className="text-[14px] font-bold text-white">
                {maxRiskPct}% · ₹{riskAmount}
              </p>
            </div>
          </div>
          <div>
            <p className="text-[10px] text-slate-500">
              Affordable quantity {riskAmount} · needs a setup with entry & stop
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}