import React from 'react';
import { T } from '../theme';

export default function PrivacyPage() {
  return (
    <div style={{ minHeight: '100vh', background: T.bg, color: T.text, fontFamily: "'Inter', system-ui, sans-serif", padding: '60px 24px' }}>
      <div style={{ maxWidth: 800, margin: '0 auto' }}>
        <header style={{ marginBottom: 48 }}>
          <h1 style={{ fontSize: 'clamp(28px, 4vw, 40px)', fontWeight: 800, margin: '0 0 12px', letterSpacing: '-0.02em' }}>Privacy Policy</h1>
          <p style={{ color: T.textMid, fontSize: 16 }}>Last updated: January 2025</p>
        </header>

        <section style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>1. Information We Collect</h2>
          <p style={{ color: T.textMid, lineHeight: 1.7, marginBottom: 16 }}>
            ApexTrade is a local-first, personal workstation. We collect minimal data:
          </p>
          <ul style={{ color: T.textMid, lineHeight: 1.8, marginBottom: 16, paddingLeft: 24 }}>
            <li><strong>Access Code:</strong> Your single access code (hashed with bcrypt, never stored in plaintext)</li>
            <li><strong>Session Token:</strong> JWT token stored in httpOnly, secure, sameSite=none cookie + localStorage mirror</li>
            <li><strong>Local Preferences:</strong> API URL, chart settings, watchlist favorites stored in localStorage (never sent to server)</li>
            <li><strong>Trading Data:</strong> Paper trades, signals, predictions, journal entries stored in local SQLite (on your machine/server)</li>
            <li><strong>Market Data Cache:</strong> OHLCV bars cached in memory for chart rendering</li>
          </ul>
          <p style={{ color: T.textMid, lineHeight: 1.7 }}>
            We do <strong>not</strong> collect: personal identification, payment info, browsing history, location, or device fingerprinting.
          </p>
        </section>

        <section style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>2. How We Use Your Data</h2>
          <ul style={{ color: T.textMid, lineHeight: 1.8, marginBottom: 16, paddingLeft: 24 }}>
            <li>Authenticate and maintain your session</li>
            <li>Store and retrieve your paper trading portfolio, orders, and journal</li>
            <li>Serve cached market data for charts</li>
            <li>Run backtests and strategy tournaments on your request</li>
            <li>Generate AI chart analyses (images sent to Gemini API, not stored)</li>
          </ul>
        </section>

        <section style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>3. Data Storage & Security</h2>
          <ul style={{ color: T.textMid, lineHeight: 1.8, marginBottom: 16, paddingLeft: 24 }}>
            <li><strong>Local-First:</strong> All trading data lives in your local SQLite database (or your PostgreSQL if self-hosted)</li>
            <li><strong>Encryption:</strong> Broker credentials encrypted with Fernet (AES-256) before storage</li>
            <li><strong>Tokens:</strong> JWT with HS256, 8-hour expiry, httpOnly secure cookies</li>
            <li><strong>Transport:</strong> HTTPS/TLS enforced in production</li>
            <li><strong>No Telemetry:</strong> No analytics, crash reporting, or usage tracking sent to third parties</li>
          </ul>
        </section>

        <section style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>4. Third-Party Services</h2>
          <p style={{ color: T.textMid, lineHeight: 1.7, marginBottom: 16 }}>
            We integrate with the following services. Your data is sent only when you explicitly use these features:
          </p>
          <ul style={{ color: T.textMid, lineHeight: 1.8, marginBottom: 16, paddingLeft: 24 }}>
            <li><strong>Google Gemini API:</strong> Chart image analysis (image + prompt sent, response returned, not stored)</li>
            <li><strong>Angel One SmartAPI:</strong> Live market data & order routing (credentials encrypted, only used when you connect)</li>
            <li><strong>Yahoo Finance / NSE:</strong> Historical data & simulated real-time market data (public endpoints)</li>
          </ul>
        </section>

        <section style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>5. Your Rights</h2>
          <ul style={{ color: T.textMid, lineHeight: 1.8, marginBottom: 16, paddingLeft: 24 }}>
            <li><strong>Access:</strong> All your data is visible in the UI (Portfolio, Journal, Predictions, Settings)</li>
            <li><strong>Deletion:</strong> Clear localStorage, delete the SQLite file, or use "Clear Order Logs" in the UI</li>
            <li><strong>Portability:</strong> Export trades, signals, predictions as CSV/JSON from respective panels</li>
            <li><strong>Revocation:</strong> Disconnect broker in Settings → revokes stored credentials</li>
          </ul>
        </section>

        <section style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>6. Data Retention</h2>
          <p style={{ color: T.textMid, lineHeight: 1.7, marginBottom: 16 }}>
            Local data persists until you delete it. No automatic expiration. Server-side (if self-hosted) retains 
            logs for 30 days for debugging. No cloud backup of your data.
          </p>
        </section>

        <section style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>7. Children's Privacy</h2>
          <p style={{ color: T.textMid, lineHeight: 1.7 }}>
            The Platform is not intended for users under 18. We do not knowingly collect data from minors.
          </p>
        </section>

        <section style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>8. Changes</h2>
          <p style={{ color: T.textMid, lineHeight: 1.7, marginBottom: 16 }}>
            We may update this policy. Continued use constitutes acceptance. Material changes will be 
            highlighted in the UI.
          </p>
        </section>

        <section style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 16 }}>9. Contact</h2>
          <p style={{ color: T.textMid, lineHeight: 1.7 }}>
            For privacy questions, contact <a href="mailto:privacy@apextrade.ai" style={{ color: T.accent, textDecoration: 'none' }}>privacy@apextrade.ai</a>.
          </p>
        </section>
      </div>
    </div>
  );
}