import React from 'react';
import { AlertTriangle, ShieldCheck, AlertCircle, Info } from 'lucide-react';
import { T } from '../theme';

export default function DisclaimerPage() {
  return (
    <div style={{ minHeight: '100vh', background: T.bg, color: T.text, fontFamily: "'Inter', system-ui, sans-serif", padding: '60px 24px' }}>
      <div style={{ maxWidth: 800, margin: '0 auto' }}>
        <header style={{ marginBottom: 48, textAlign: 'center' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 12, padding: '16px 24px', background: 'rgba(255,61,90,0.1)', border: '1px solid rgba(255,61,90,0.3)', borderRadius: 12, marginBottom: 24 }}>
            <AlertTriangle size={28} color="#ff3d5a" />
            <span style={{ fontSize: 18, fontWeight: 700, color: '#ff3d5a', letterSpacing: '0.04em' }}>IMPORTANT RISK DISCLAIMER</span>
          </div>
          <h1 style={{ fontSize: 'clamp(28px, 4vw, 40px)', fontWeight: 800, margin: '0 0 12px', letterSpacing: '-0.02em' }}>Risk Disclaimer & Disclaimer</h1>
          <p style={{ color: T.textMid, fontSize: 16 }}>Read carefully before using ApexTrade AI</p>
        </header>

        <section style={{ marginBottom: 32, padding: '24px', background: 'rgba(255,61,90,0.05)', border: '1px solid rgba(255,61,90,0.2)', borderRadius: 12 }}>
          <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
            <AlertCircle size={24} color="#ff3d5a" style={{ flexShrink: 0, marginTop: 2 }} />
            <div style={{ color: T.textMid, lineHeight: 1.8 }}>
              <p style={{ fontWeight: 700, marginBottom: 8, fontSize: 16 }}>⚠️ THIS IS A PAPER-TRADING WORKSTATION FOR EDUCATIONAL PURPOSES ONLY.</p>
              <p style={{ color: T.textMid, lineHeight: 1.7 }}>
                ApexTrade AI does <strong>not</strong> execute real trades. No real money is at risk. 
                All trades, P&L, signals, and performance metrics are <strong>simulated</strong> using historical 
                or real-time market data. No real orders are sent to any broker or exchange.
              </p>
            </div>
          </div>
        </section>

        <section style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>1. Not Financial Advice</h2>
          <p style={{ color: T.textMid, lineHeight: 1.7, marginBottom: 16 }}>
            ApexTrade AI is <strong>not</strong> a registered investment advisor. The Platform does not provide 
            personalized financial advice, investment recommendations, or portfolio management services. 
            All signals, patterns, predictions, and AI-generated analyses are algorithmic outputs for 
            informational and educational purposes only.
          </p>
          <p style={{ color: T.textMid, lineHeight: 1.7 }}>
            You should consult with a qualified financial advisor or SEBI-registered investment advisor 
            before making any investment decisions.
          </p>
        </section>

        <section style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>2. Not SEBI Registered</h2>
          <p style={{ color: T.textMid, lineHeight: 1.7, marginBottom: 16 }}>
            ApexTrade AI is <strong>not registered</strong> with the Securities and Exchange Board of India (SEBI) 
            as an investment advisor, portfolio manager, or research analyst. The Platform operates as a 
            technology tool for personal research and paper trading simulation only.
          </p>
        </section>

        <section style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>3. No Guarantee of Accuracy</h2>
          <p style={{ color: T.textMid, lineHeight: 1.7, marginBottom: 16 }}>
            All signals, patterns, predictions, AI analyses, and market data are generated algorithmically 
            and may contain errors, delays, or omissions. Market data is sourced from third-party providers 
            and may be delayed, incomplete, or inaccurate. AI-generated analyses (chart scans, reasoning) 
            are probabilistic and may be incorrect.
          </p>
        </section>

        <section style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>4. Past Performance ≠ Future Results</h2>
          <p style={{ color: T.textMid, lineHeight: 1.7, marginBottom: 16 }}>
            Backtest results, tournament scores, win rates, and paper trading P&L are based on historical 
            data and <strong>do not guarantee future performance</strong>. Market conditions change. 
            Strategies that worked in the past may fail in the future.
          </p>
        </section>

        <section style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>5. Paper Trading ≠ Live Trading</h2>
          <p style={{ color: T.textMid, lineHeight: 1.7, marginBottom: 16 }}>
            Paper trading results <strong>do not reflect real-world outcomes</strong>. Live trading involves:
          </p>
          <ul style={{ color: T.textMid, lineHeight: 1.8, marginBottom: 16, paddingLeft: 24 }}>
            <li>Slippage, commissions, and exchange fees</li>
            <li>Partial fills, rejections, and order latency</li>
            <li>Psychological pressure with real capital at risk</li>
            <li>Liquidity constraints and market impact</li>
            <li>Regulatory and tax implications</li>
          </ul>
          <p style={{ color: T.textMid, lineHeight: 1.7 }}>
            Paper trading results <strong>cannot be extrapolated</strong> to live trading performance.
          </p>
        </section>

        <section style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>6. Data & AI Limitations</h2>
          <ul style={{ color: T.textMid, lineHeight: 1.8, marginBottom: 16, paddingLeft: 24 }}>
            <li>Market data sourced from third parties (NSE, Angel One, Yahoo Finance) — may be delayed, incomplete, or erroneous</li>
            <li>AI chart analysis (Gemini 2.0 Flash) is probabilistic — may hallucinate patterns or miss key levels</li>
            <li>Backtests use historical data with assumptions (slippage models, commission estimates) that may not match reality</li>
            <li>Strategy tournament scores are relative rankings, not absolute performance guarantees</li>
          </ul>
        </section>

        <section style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>7. No Liability</h2>
          <p style={{ color: T.textMid, lineHeight: 1.7, marginBottom: 16 }}>
            ApexTrade AI, its developers, and affiliates shall <strong>not be liable</strong> for any losses, 
            damages, or missed opportunities arising from your use of the Platform, including but not limited to:
          </p>
          <ul style={{ color: T.textMid, lineHeight: 1.8, marginBottom: 16, paddingLeft: 24 }}>
            <li>Trading losses (paper or live)</li>
            <li>Missed opportunities or delayed signals</li>
            <li>Data errors, delays, or outages</li>
            <li>AI hallucinations or incorrect analyses</li>
            <li>Software bugs or platform downtime</li>
          </ul>
        </section>

        <section style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>8. Your Responsibility</h2>
          <p style={{ color: T.textMid, lineHeight: 1.7, marginBottom: 16 }}>
            You are <strong>solely responsible</strong> for all trading decisions made using this Platform. 
            This includes:
          </p>
          <ul style={{ color: T.textMid, lineHeight: 1.8, marginBottom: 16, paddingLeft: 24 }}>
            <li>Verifying all signals and data independently</li>
            <li>Understanding the risks of any strategy before deploying</li>
            <li>Setting appropriate risk limits and position sizes</li>
            <li>Complying with all applicable laws and regulations (SEBI, tax laws, etc.)</li>
            <li>Never trading with money you cannot afford to lose</li>
          </ul>
        </section>

        <section style={{ marginBottom: 32, padding: '24px', background: 'rgba(0,245,160,0.05)', border: '1px solid rgba(0,245,160,0.2)', borderRadius: 12 }}>
          <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
            <ShieldCheck size={24} color="#00f5a0" style={{ flexShrink: 0, marginTop: 2 }} />
            <div style={{ color: T.textMid, lineHeight: 1.8 }}>
              <p style={{ fontWeight: 700, marginBottom: 8, fontSize: 16 }}>✅ REMEMBER</p>
              <p style={{ color: T.textMid, lineHeight: 1.7 }}>
                <strong>Paper trading is practice. Live trading is different.</strong> Never risk money you cannot afford to lose. 
                Always do your own research. Never blindly follow signals — not even from ApexTrade AI.
              </p>
            </div>
          </div>
        </section>

        <section style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>9. Regulatory Notice</h2>
          <p style={{ color: T.textMid, lineHeight: 1.7, marginBottom: 16 }}>
            ApexTrade AI is <strong>not registered</strong> with SEBI (Securities and Exchange Board of India) 
            as an Investment Adviser, Portfolio Manager, Research Analyst, or Stock Broker. 
            The Platform is a technology tool for personal research and paper trading simulation.
          </p>
        </section>

        <section style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>10. Contact</h2>
          <p style={{ color: T.textMid, lineHeight: 1.7 }}>
            For questions about this disclaimer, contact 
            <a href="mailto:legal@apextrade.ai" style={{ color: T.accent, textDecoration: 'none' }}>legal@apextrade.ai</a>.
          </p>
        </section>

        <footer style={{ marginTop: 64, paddingTop: 32, borderTop: `1px solid ${T.border}`, textAlign: 'center', color: T.textMid, fontSize: 13 }}>
          <p style={{ marginBottom: 8 }}>&copy; 2025 ApexTrade AI. All rights reserved.</p>
          <p style={{ fontSize: 12, opacity: 0.7 }}>This disclaimer is part of the Terms of Service. Last updated: January 2025</p>
        </footer>
      </div>
    </div>
  );
}