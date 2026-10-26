import React from 'react';
import { T } from '../theme';

export default function TermsPage() {
  return (
    <div style={{ minHeight: '100vh', background: T.bg, color: T.text, fontFamily: "'Inter', system-ui, sans-serif", padding: '60px 24px' }}>
      <div style={{ maxWidth: 800, margin: '0 auto' }}>
        <header style={{ marginBottom: 48 }}>
          <h1 style={{ fontSize: 'clamp(28px, 4vw, 40px)', fontWeight: 800, margin: '0 0 12px', letterSpacing: '-0.02em' }}>Terms of Service</h1>
          <p style={{ color: T.textMid, fontSize: 16 }}>Last updated: January 2025</p>
        </header>

        <section style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>1. Acceptance of Terms</h2>
          <p style={{ color: T.textMid, lineHeight: 1.7, marginBottom: 16 }}>
            By accessing or using ApexTrade AI ("the Platform"), you agree to be bound by these Terms of Service ("Terms").
            If you do not agree with any part of these Terms, you may not use the Platform.
          </p>
        </section>

        <section style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>2. Description of Service</h2>
          <p style={{ color: T.textMid, lineHeight: 1.7, marginBottom: 16 }}>
            ApexTrade AI is a paper-trading workstation for algorithmic trading research and education.
            The Platform provides:
          </p>
          <ul style={{ color: T.textMid, lineHeight: 1.8, marginBottom: 16, paddingLeft: 24 }}>
            <li>Simulated NSE market data via WebSocket and HTTP fallback</li>
            <li>AI-powered chart analysis using Gemini 2.0 Flash</li>
            <li>Paper trading simulation with 30+ quantitative strategies</li>
            <li>30-strategy tournament backtesting across 10-year historical datasets</li>
            <li>Risk management tools (position sizing, drawdown limits, ATR stops)</li>
          </ul>
          <p style={{ color: T.textMid, lineHeight: 1.7, marginBottom: 16 }}>
            <strong>Important:</strong> ApexTrade is a paper-trading workstation for educational and research purposes only.
            No real money is traded. No real orders are executed on any exchange.
          </p>
        </section>

        <section style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>3. No Financial Advice</h2>
          <p style={{ color: T.textMid, lineHeight: 1.7, marginBottom: 16 }}>
            The Platform does not provide financial advice, investment recommendations, or personalized trading advice.
            All signals, patterns, predictions, and analyses are generated algorithmically for informational purposes only.
            Past performance does not guarantee future results.
          </p>
          <p style={{ color: T.textMid, lineHeight: 1.7, marginBottom: 16 }}>
            You are solely responsible for your own trading decisions. Always do your own research and consult
            with a qualified financial advisor before making any investment decisions.
          </p>
        </section>

        <section style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>4. Paper Trading Only</h2>
          <p style={{ color: T.textMid, lineHeight: 1.7, marginBottom: 16 }}>
            ApexTrade operates in paper trading mode by default. No real orders are sent to any broker or exchange.
            All trades, P&L, and performance metrics are simulated using historical or simulated real-time market data.
            No real money is at risk.
          </p>
          <p style={{ color: T.textMid, lineHeight: 1.7, marginBottom: 16 }}>
            Live trading is not available in this personal workstation build; the bot runs in paper mode only.
            You are solely responsible for any trading decisions you make outside this platform.
          </p>
        </section>

        <section style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>5. Data & Accuracy</h2>
          <p style={{ color: T.textMid, lineHeight: 1.7, marginBottom: 16 }}>
            Market data is sourced from third-party providers (NSE, Angel One, Yahoo Finance) and may contain errors,
            delays, or omissions. ApexTrade does not guarantee the accuracy, completeness, or timeliness of any data.
            AI-generated analyses (chart scans, signal reasoning) are probabilistic and may be incorrect.
          </p>
        </section>

        <section style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>6. User Responsibilities</h2>
          <ul style={{ color: T.textMid, lineHeight: 1.8, marginBottom: 16, paddingLeft: 24 }}>
            <li>You are responsible for maintaining the confidentiality of your access code</li>
            <li>You must not attempt to reverse engineer, decompile, or exploit the Platform</li>
            <li>You must not use the Platform for any illegal or unauthorized purpose</li>
            <li>You are responsible for all activity under your account</li>
          </ul>
        </section>

        <section style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>7. Intellectual Property</h2>
          <p style={{ color: T.textMid, lineHeight: 1.7, marginBottom: 16 }}>
            All rights, title, and interest in the Platform (including software, algorithms, UI, and content)
            remain the property of ApexTrade. You may not copy, modify, distribute, or create derivative works
            without express written permission.
          </p>
        </section>

        <section style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>8. Disclaimer of Warranties</h2>
          <p style={{ color: T.textMid, lineHeight: 1.7, marginBottom: 16 }}>
            THE PLATFORM IS PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT WARRANTIES OF ANY KIND,
            EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO IMPLIED WARRANTIES OF
            MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.
          </p>
        </section>

        <section style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>9. Limitation of Liability</h2>
          <p style={{ color: T.textMid, lineHeight: 1.7, marginBottom: 16 }}>
            IN NO EVENT SHALL APEXTRADE BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL,
            OR PUNITIVE DAMAGES, INCLUDING LOSS OF PROFITS, DATA, OR BUSINESS OPPORTUNITIES,
            ARISING FROM OR RELATED TO YOUR USE OF THE PLATFORM.
          </p>
        </section>

        <section style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>10. Governing Law</h2>
          <p style={{ color: T.textMid, lineHeight: 1.7, marginBottom: 16 }}>
            These Terms shall be governed by the laws of India. Any disputes shall be subject to the
            exclusive jurisdiction of the courts in Mumbai, Maharashtra.
          </p>
        </section>

        <section style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>11. Changes to Terms</h2>
          <p style={{ color: T.textMid, lineHeight: 1.7, marginBottom: 16 }}>
            We may update these Terms from time to time. Continued use of the Platform after changes
            constitutes acceptance of the new Terms.
          </p>
        </section>

        <section style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>12. Contact</h2>
          <p style={{ color: T.textMid, lineHeight: 1.7 }}>
            For questions about these Terms, contact us at <a href="mailto:legal@apextrade.ai" style={{ color: T.accent, textDecoration: 'none' }}>legal@apextrade.ai</a>.
          </p>
        </section>
      </div>
    </div>
  );
}