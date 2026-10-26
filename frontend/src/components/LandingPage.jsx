import React from 'react';
import { ArrowRight, ShieldCheck, BarChart3, Zap, AlertCircle, Mail, Github, Twitter } from 'lucide-react';
import { T } from '../theme';

export default function LandingPage() {
  return (
    <div style={{ minHeight: '100vh', background: T.bg, color: T.text, fontFamily: "'Inter', system-ui, sans-serif" }}>
      {/* Hero Section */}
      <section style={{ minHeight: '90vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '80px 24px', position: 'relative', overflow: 'hidden' }}>
        <div style={{ position: 'absolute', inset: 0, background: 'radial-gradient(ellipse at center, rgba(99,102,241,0.08) 0%, transparent 70%)', pointerEvents: 'none' }} />
        <div style={{ position: 'absolute', top: '20%', left: '10%', width: '400px', height: '400px', background: 'radial-gradient(circle, rgba(0,245,160,0.04) 0%, transparent 70%)', borderRadius: '50%', pointerEvents: 'none', animation: 'float 20s ease-in-out infinite' }} />
        <div style={{ position: 'absolute', bottom: '10%', right: '10%', width: '300px', height: '300px', background: 'radial-gradient(circle, rgba(245,200,66,0.04) 0%, transparent 70%)', borderRadius: '50%', pointerEvents: 'none', animation: 'float 25s ease-in-out infinite reverse' }} />
        
        <style jsx>{`
          @keyframes float {
            0%, 100% { transform: translate(0, 0); }
            50% { transform: translate(30px, -20px); }
          }
        `}</style>

        <div style={{ position: 'relative', zIndex: 1, maxWidth: 800, textAlign: 'center', width: '100%' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '8px 16px', borderRadius: 999, background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.25)', marginBottom: 24 }}>
            <span style={{ fontSize: 14, fontWeight: 700, color: T.accent, letterSpacing: '0.12em' }}>APEX TRADE AI</span>
          </div>
          
          <h1 style={{ fontSize: 'clamp(36px, 6vw, 56px)', fontWeight: 800, letterSpacing: '-0.03em', margin: '0 0 16px', lineHeight: 1.1, background: 'linear-gradient(135deg, #ffffff 30%, #a855f7 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            Your Personal Quant Workstation
          </h1>
          
          <p style={{ fontSize: 'clamp(16px, 2.5vw, 20px)', color: T.textMid, margin: '0 0 32px', maxWidth: 600, marginLeft: 'auto', marginRight: 'auto', lineHeight: 1.6 }}>
            An institutional-grade algorithmic trading workstation for the personal quant. 
            Simulated NSE price data, AI-powered chart analysis, autonomous paper trading, and 30-strategy backtesting — all in a clean, dark terminal.
          </p>

          <div style={{ display: 'flex', gap: 16, justifyContent: 'center', flexWrap: 'wrap', marginBottom: 48 }}>
            <a href="#features" style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '14px 28px', background: T.accent, color: '#0b0e13', borderRadius: 8, fontWeight: 700, fontSize: 14, textDecoration: 'none', fontFamily: "'Inter', sans-serif", transition: 'all 0.2s' }}>
              <ArrowRight size={16} /> Explore Features
            </a>
            <a href="#demo" style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '14px 28px', background: 'transparent', color: T.text, border: `1px solid ${T.border}`, borderRadius: 8, fontWeight: 700, fontSize: 14, textDecoration: 'none', fontFamily: "'Inter', sans-serif", transition: 'all 0.2s' }}>
              View Demo
            </a>
          </div>

          {/* Trust Indicators */}
          <div style={{ display: 'flex', gap: 32, justifyContent: 'center', flexWrap: 'wrap', color: T.textDim, fontSize: 13, fontFamily: "'IBM Plex Mono', monospace" }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <ShieldCheck size={14} color={T.green} /> Enterprise-grade security
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <BarChart3 size={14} color={T.blue} /> 30-strategy backtesting
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <Zap size={14} color={'#f5c842'} /> Simulated NSE feed
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" style={{ padding: '100px 24px', background: T.surface, borderTop: `1px solid ${T.border}` }}>
        <div style={{ maxWidth: 1000, margin: '0 auto' }}>
          <header style={{ textAlign: 'center', marginBottom: 64 }}>
            <span style={{ display: 'inline-block', padding: '6px 14px', background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.25)', borderRadius: 999, fontSize: 12, fontWeight: 700, color: T.accent, letterSpacing: '0.1em', marginBottom: 16 }}>CORE CAPABILITIES</span>
            <h2 style={{ fontSize: 'clamp(28px, 4vw, 40px)', fontWeight: 800, margin: '0 0 12px', letterSpacing: '-0.02em' }}>Built for the Serious Quant</h2>
            <p style={{ color: T.textMid, fontSize: 16, maxWidth: 600, margin: '0 auto' }}>Every feature is designed for institutional-grade workflows — no toy features, no fluff.</p>
          </header>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 24 }}>
            <FeatureCard icon={BarChart3} title="30-Strategy Tournament" desc="Run 30 quantitative strategies across 26 local 10-year datasets. Automated leaderboard with score, win rate, Sharpe, and max drawdown." />
            <FeatureCard icon={Zap} title="Simulated NSE Feed" desc="Simulated tick data via WebSocket with HTTP fallback. Market hours awareness (IST), pre-market/closed states, and tick animations." />
            <FeatureCard icon={ShieldCheck} title="AI Chart Analysis" desc="Upload any candlestick screenshot — Gemini 2.0 Flash returns trend, patterns, support/resistance, breakout signals with confidence meter." />
            <FeatureCard icon={BarChart3} title="Autonomous Paper Bot" desc="Paper trading bot with strategy selection, risk controls, drawdown limits, and full trade log. One-click start/pause/stop." />
            <FeatureCard icon={AlertCircle} title="Risk-First Architecture" desc="Per-trade 2% risk cap, daily loss limits, max consecutive losses guard, ATR-based stops. Paper mode only by default." />
            <FeatureCard icon={BarChart3} title="Full Audit Trail" desc="Every signal, prediction, trade, and AI analysis logged with timestamps. Exportable CSV/JSON for compliance." />
          </div>
        </div>
      </section>

      {/* Sample Signal */}
      <section id="demo" style={{ padding: '100px 24px', background: T.bg, borderTop: `1px solid ${T.border}` }}>
        <div style={{ maxWidth: 800, margin: '0 auto' }}>
          <header style={{ textAlign: 'center', marginBottom: 48 }}>
            <span style={{ display: 'inline-block', padding: '6px 14px', background: 'rgba(0,245,160,0.1)', border: '1px solid rgba(0,245,160,0.25)', borderRadius: 999, fontSize: 12, fontWeight: 700, color: '#00f5a0', letterSpacing: '0.1em', marginBottom: 16 }}>SAMPLE SIGNAL</span>
            <h2 style={{ fontSize: 'clamp(28px, 4vw, 40px)', fontWeight: 800, margin: '0 0 12px' }}>What a Signal Looks Like</h2>
            <p style={{ color: T.textMid, fontSize: 16, maxWidth: 600, margin: '0 auto' }}>Paper trading only. This is a representative sample, not live market data.</p>
          </header>

          <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 16, padding: 24, maxWidth: 600, margin: '0 auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16, flexWrap: 'wrap', gap: 12 }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                  <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', color: T.accent, fontFamily: "'IBM Plex Mono', monospace" }}>NIFTY</span>
                  <span style={{ background: 'rgba(0,245,160,0.1)', color: '#00f5a0', padding: '2px 8px', borderRadius: 999, fontSize: 10, fontWeight: 700, fontFamily: "'IBM Plex Mono', monospace" }}>BUY</span>
                </div>
                <div style={{ fontSize: 12, color: T.textMid, fontFamily: "'IBM Plex Mono', monospace" }}>Nifty 50 Index</div>
              </div>
              <div style={{ textAlign: 'right', minWidth: 140 }}>
                <div style={{ fontSize: 24, fontWeight: 700, color: T.text, fontFamily: "'IBM Plex Mono', monospace" }}>₹24,532.15</div>
                <div style={{ color: '#00f5a0', fontSize: 12, fontWeight: 700, fontFamily: "'IBM Plex Mono', monospace" }}>+0.84% (+204.30)</div>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 20 }}>
              <StatBox label="ENTRY" value="₹24,450" color="#38bdf8" />
              <StatBox label="TARGET" value="₹25,200" color="#f5c842" />
              <StatBox label="STOP" value="₹24,100" color="#ff3d5a" />
            </div>

            <div style={{ borderTop: `1px solid ${T.border}`, paddingTop: 16 }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: T.textMid, letterSpacing: '0.08em', marginBottom: 8, fontFamily: "'IBM Plex Mono', monospace" }}>REASONING</div>
              <p style={{ color: T.text, lineHeight: 1.6, fontSize: 13 }}>RSI(14) at 32 indicates oversold on daily timeframe. Volume spike 2.3x 20-day average confirms accumulation. EMA(9) crossing above EMA(21) on 4H chart. MACD histogram turning positive. Risk-reward 1:2.5.</p>
            </div>

            <div style={{ marginTop: 20, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 12px', background: 'rgba(0,245,160,0.1)', border: '1px solid rgba(0,245,160,0.3)', borderRadius: 999, fontSize: 11, fontWeight: 600, color: '#00f5a0' }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#00f5a0' }} /> Confidence: 87%
              </span>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 12px', background: 'rgba(245,200,66,0.1)', border: '1px solid rgba(245,200,66,0.3)', borderRadius: 999, fontSize: 11, fontWeight: 600, color: '#f5c842' }}>
                R:R 1:2.5
              </span>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 12px', background: 'rgba(56,189,248,0.1)', border: '1px solid rgba(56,189,248,0.3)', borderRadius: 999, fontSize: 11, fontWeight: 600, color: '#38bdf8' }}>
                Intraday (5m-15m)
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section style={{ padding: '100px 24px', background: T.surface, borderTop: `1px solid ${T.border}` }}>
        <div style={{ maxWidth: 600, margin: '0 auto', textAlign: 'center' }}>
          <h2 style={{ fontSize: 'clamp(28px, 4vw, 40px)', fontWeight: 800, margin: '0 0 16px' }}>Ready to Start?</h2>
          <p style={{ color: T.textMid, fontSize: 16, marginBottom: 32 }}>Join quants who trade with institutional tools. Paper trading only — no risk, all insight.</p>
          <div style={{ display: 'flex', gap: 16, justifyContent: 'center', flexWrap: 'wrap' }}>
            <button style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '14px 28px', background: T.accent, color: '#0b0e13', borderRadius: 8, fontWeight: 700, fontSize: 14, border: 'none', cursor: 'pointer', fontFamily: "'Inter', sans-serif" }}>
              Launch Terminal (Paper Mode)
            </button>
            <a href="mailto:support@apextrade.ai" style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '14px 28px', background: 'transparent', color: T.text, border: `1px solid ${T.border}`, borderRadius: 8, fontWeight: 700, fontSize: 14, textDecoration: 'none', fontFamily: "'Inter', sans-serif" }}>
              <Mail size={16} /> Contact Support
            </a>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer style={{ padding: '60px 24px', background: T.bg, borderTop: `1px solid ${T.border}` }}>
        <div style={{ maxWidth: 1000, margin: '0 auto' }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 48, justifyContent: 'space-between', marginBottom: 48 }}>
            <div style={{ minWidth: 200 }}>
              <div style={{ fontSize: 18, fontWeight: 800, letterSpacing: '-0.02em', marginBottom: 8 }}>ApexTrade</div>
              <p style={{ color: T.textMid, fontSize: 13, lineHeight: 1.6, maxWidth: 280 }}>Personal quant workstation for algorithmic trading. Built for discipline, not gambling.</p>
            </div>
            <nav style={{ display: 'flex', flexWrap: 'wrap', gap: 32 }}>
              <div>
                <h4 style={{ fontSize: 11, fontWeight: 700, color: T.textMid, letterSpacing: '0.1em', marginBottom: 12, textTransform: 'uppercase' }}>Product</h4>
                <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <li><a href="#features" style={{ color: T.textMid, fontSize: 13, textDecoration: 'none' }}>Features</a></li>
                  <li><a href="#demo" style={{ color: T.textMid, fontSize: 13, textDecoration: 'none' }}>Demo</a></li>
                  <li><a href="https://github.com/apextrade" target="_blank" rel="noopener noreferrer" style={{ color: T.textMid, fontSize: 13, textDecoration: 'none' }}>GitHub</a></li>
                </ul>
              </div>
              <div>
                <h4 style={{ fontSize: 11, fontWeight: 700, color: T.textMid, letterSpacing: '0.1em', marginBottom: 12, textTransform: 'uppercase' }}>Legal</h4>
                <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <li><a href="/terms" style={{ color: T.textMid, fontSize: 13, textDecoration: 'none' }}>Terms of Service</a></li>
                  <li><a href="/privacy" style={{ color: T.textMid, fontSize: 13, textDecoration: 'none' }}>Privacy Policy</a></li>
                  <li><a href="/disclaimer" style={{ color: T.textMid, fontSize: 13, textDecoration: 'none' }}>Risk Disclaimer</a></li>
                </ul>
              </div>
              <div>
                <h4 style={{ fontSize: 11, fontWeight: 700, color: T.textMid, letterSpacing: '0.1em', marginBottom: 12, textTransform: 'uppercase' }}>Connect</h4>
                <div style={{ display: 'flex', gap: 16 }}>
                  <a href="https://github.com/apextrade" target="_blank" rel="noopener noreferrer" style={{ color: T.textMid }}><Github size={18} /></a>
                  <a href="https://twitter.com/apextrade" target="_blank" rel="noopener noreferrer" style={{ color: T.textMid }}><Twitter size={18} /></a>
                  <a href="mailto:support@apextrade.ai" style={{ color: T.textMid }}><Mail size={18} /></a>
                </div>
              </div>
            </nav>
          </div>
          <div style={{ borderTop: `1px solid ${T.border}`, paddingTop: 24, textAlign: 'center', color: T.textDim, fontSize: 12 }}>
            <p>⚠️ <strong>Risk Disclaimer:</strong> ApexTrade is a paper-trading workstation for educational and research purposes only. Not SEBI registered advice. Past performance ≠ future results. Trade responsibly.</p>
            <p style={{ marginTop: 12 }}>&copy; 2025 ApexTrade AI. All rights reserved.</p>
          </div>
        </div>
      </footer>

      <style jsx>{`
        .feature-card {
          background: ${T.surface};
          border: '1px solid ${T.border}';
          border-radius: '12px';
          padding: '24px';
          transition: 'all 0.2s';
        }
        .feature-card:hover {
          border-color: ${T.accent};
          box-shadow: '0 8px 32px rgba(99,102,241,0.15)';
        }
        .stat-box {
          background: ${T.bg};
          border: '1px solid ${T.border}';
          border-radius: '10px';
          padding: '16px';
          text-align: 'center';
        }
        .stat-label {
          font-size: 10px;
          font-weight: 700;
          color: ${T.textMid};
          letter-spacing: 0.08em;
          font-family: "'IBM Plex Mono', monospace";
          margin-bottom: 4px;
        }
        .stat-value {
          font-size: 20px;
          font-weight: 700;
          color: ${(props) => props.color};
          font-family: "'IBM Plex Mono', monospace";
        }
      `}
      </style>
    </div>
  );
}

function FeatureCard({ icon: Icon, title, desc }) {
  return (
    <div className="feature-card" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Icon size={28} color={T.accent} />
      <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>{title}</h3>
      <p style={{ color: T.textMid, lineHeight: 1.6, margin: 0, fontSize: 14 }}>{desc}</p>
    </div>
  );
}

function StatBox({ label, value, color }) {
  return (
    <div className="stat-box">
      <div className="stat-label">{label}</div>
      <div className="stat-value" style={{ color }}>{value}</div>
    </div>
  );
}