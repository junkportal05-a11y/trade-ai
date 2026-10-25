import { getApiBaseUrl, setApiBaseUrl } from './api';
import { formatError } from './utils/formatError';
import React, { useState, useEffect } from 'react';
import { Server, ShieldCheck, ArrowRight, Activity, Lock, RefreshCw, Cpu, Zap, Eye, EyeOff } from 'lucide-react';

function getTimeoutSignal(ms) {
  if (typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function') {
    return AbortSignal.timeout(ms);
  }
  const controller = new AbortController();
  setTimeout(() => controller.abort(), ms);
  return controller.signal;
}

const T = {
  bg: '#07090e',
  surface: '#0d111a',
  panel: '#111622',
  panelAlt: '#141a29',
  border: '#1b2234',
  borderHi: '#2c3652',
  text: '#e2e8f0',
  textMid: '#8290ad',
  textDim: '#475470',
  accent: '#6366f1',
  accentAlt: '#a855f7',
  green: '#00f5a0',
  blue: '#38bdf8',
  gold: '#fbbf24',
  red: '#ff3366',
};

const mono = { fontFamily: "'JetBrains Mono', 'IBM Plex Mono', monospace" };

const HF_DEFAULT_URL = "https://apextrade-core-trade-ai-backend.hf.space";
const LOCAL_DEFAULT_URL = "http://localhost:7860";

export default function LoginScreen({ onLogin }) {
  const [accessCode, setAccessCode] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showCustomUrl, setShowCustomUrl] = useState(false);
  const [customInput, setCustomInput] = useState('');

  const [currentUrl, setCurrentUrl] = useState(() => getApiBaseUrl() || (typeof window !== "undefined" && window.location.hostname === 'localhost' ? LOCAL_DEFAULT_URL : HF_DEFAULT_URL));
  const [serverReady, setServerReady] = useState(false);
  const [waking, setWaking] = useState(true);
  const [latency, setLatency] = useState(null);

  // Pre-warm / probe backend status
  useEffect(() => {
    let cancelled = false;

    const probe = async () => {
      setWaking(true);
      const target = currentUrl.replace(/\/$/, "");
      const start = performance.now();

      try {
        const r = await fetch(`${target}/api/health`, {
          method: "GET",
          signal: getTimeoutSignal(6000)
        }).catch(() => fetch(`${target}/`, { method: "GET", signal: getTimeoutSignal(6000) }));

        if (r && r.ok && !cancelled) {
          const lat = Math.round(performance.now() - start);
          setServerReady(true);
          setLatency(lat);
          setWaking(false);
          return;
        }
      } catch (_) {}

      if (!cancelled) {
        setServerReady(false);
        setWaking(false);
      }
    };

    probe();
    const interval = setInterval(probe, 8000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [currentUrl]);

  const handleSwitchUrl = (newUrl) => {
    const clean = (newUrl || '').trim();
    if (!clean) return;
    setApiBaseUrl(clean);
    setCurrentUrl(clean);
    setError('');
  };

  const handleGuestEntry = () => {
    localStorage.setItem('is_logged_in', 'true');
    localStorage.setItem('apex_user', 'Guest Trader');
    localStorage.setItem('apex_role', 'Authorized Guest');
    localStorage.setItem('apex_clearance', 'LEVEL_1_GUEST');
    onLogin('Guest Trader', 'Authorized Guest', 'LEVEL_1_GUEST');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    const code = accessCode.trim();
    if (!code) {
      setError("Please enter your security access code.");
      return;
    }

    setLoading(true);

    // Offline bypass fallback for developer codes
    if (code.toLowerCase() === 'admin' || code.toLowerCase() === 'apex') {
      localStorage.setItem('is_logged_in', 'true');
      localStorage.setItem('apex_user', 'Lead Quant');
      localStorage.setItem('apex_role', 'Administrator');
      localStorage.setItem('apex_clearance', 'LEVEL_3_ADMIN');
      onLogin('Lead Quant', 'Administrator', 'LEVEL_3_ADMIN');
      setLoading(false);
      return;
    }

    const target = currentUrl.replace(/\/$/, "");
    const payload = JSON.stringify({ username: "code", password: code });

    try {
      const res = await fetch(`${target}/api/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: payload,
        signal: getTimeoutSignal(10000),
      });

      if (!res.ok) {
        let errMessage = "AUTHENTICATION FAILED: Invalid access code.";
        try {
          const errData = await res.json();
          if (errData && (errData.detail || errData.message)) {
            errMessage = "ERROR: " + formatError(errData.detail || errData.message, errMessage);
          }
        } catch (_) {}
        setError(errMessage);
        setLoading(false);
        return;
      }

      const data = await res.json();
      localStorage.setItem('is_logged_in', 'true');
      if (data.token) {
        sessionStorage.setItem('apt_token', data.token);
        localStorage.setItem('apt_token', data.token);
      }
      onLogin(data.username, data.role, data.clearance);
    } catch (err) {
      setError("CONNECTION ERROR: Backend server unreachable. Click 'Launch in Guest / Offline Mode' below to enter immediately.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: T.bg,
      color: T.text,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 20,
      fontFamily: "'Inter', sans-serif",
      zIndex: 99999,
      overflow: 'hidden',
    }}>
      {/* Background glow effects */}
      <div style={{
        position: 'absolute',
        width: '55vw',
        height: '55vw',
        background: `radial-gradient(circle, rgba(99, 102, 241, 0.08) 0%, transparent 65%)`,
        top: '10%',
        left: '20%',
        pointerEvents: 'none',
      }} />

      {/* Main Glassmorphic Card */}
      <div style={{
        width: '100%',
        maxWidth: 440,
        background: 'rgba(17, 22, 34, 0.75)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderRadius: 16,
        padding: '30px 26px',
        boxShadow: '0 24px 64px -12px rgba(0, 0, 0, 0.65), 0 0 1px 1px rgba(99, 102, 241, 0.2)',
        display: 'flex',
        flexDirection: 'column',
        gap: 22,
        position: 'relative',
        zIndex: 2,
      }}>
        {/* Card Header & Server Beacon */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', gap: 6 }}>
            <span style={{ width: 9, height: 9, borderRadius: '50%', background: '#ef4444' }} />
            <span style={{ width: 9, height: 9, borderRadius: '50%', background: '#eab308' }} />
            <span style={{ width: 9, height: 9, borderRadius: '50%', background: '#22c55e' }} />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
            <span style={{
              width: 7, height: 7, borderRadius: '50%',
              background: waking ? T.gold : serverReady ? T.green : T.red,
              boxShadow: waking ? `0 0 8px ${T.gold}` : serverReady ? `0 0 8px ${T.green}` : `0 0 8px ${T.red}`,
              animation: waking ? 'pulse 1.2s ease-in-out infinite' : 'none',
            }} />
            <span style={{ fontSize: 9.5, fontWeight: 700, color: serverReady ? T.green : T.textDim, letterSpacing: '0.1em', ...mono }}>
              {waking ? 'PROBING...' : serverReady ? `SERVER ONLINE (${latency || 12}ms)` : 'SERVER OFFLINE'}
            </span>
          </div>
        </div>

        {/* Branding */}
        <div style={{ textAlign: 'center' }}>
          <div style={{
            fontSize: 22,
            fontWeight: 800,
            letterSpacing: '0.12em',
            background: `linear-gradient(135deg, #ffffff 40%, ${T.accentAlt} 100%)`,
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            marginBottom: 4,
            ...mono,
          }}>
            ◈ APEXTRADE AI
          </div>
          <div style={{ fontSize: 10, fontWeight: 700, color: T.textMid, letterSpacing: '0.1em', ...mono }}>
            QUANTITATIVE TRADING WORKSTATION
          </div>
        </div>

        {/* Server Target Switcher Pills */}
        <div style={{
          padding: '8px 10px',
          background: 'rgba(0,0,0,0.3)',
          borderRadius: 8,
          border: '1px solid rgba(255,255,255,0.05)',
          display: 'flex',
          flexDirection: 'column',
          gap: 6,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 9.5, color: T.textDim, letterSpacing: '0.06em', ...mono }}>SERVER TARGET</span>
            <span style={{ fontSize: 9.5, color: T.blue, ...mono, overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 220 }}>
              {currentUrl}
            </span>
          </div>

          <div style={{ display: 'flex', gap: 6, marginTop: 2 }}>
            <button
              type="button"
              onClick={() => handleSwitchUrl(LOCAL_DEFAULT_URL)}
              style={{
                flex: 1, padding: '5px 8px', borderRadius: 6,
                background: currentUrl === LOCAL_DEFAULT_URL ? 'rgba(99,102,241,0.25)' : 'rgba(255,255,255,0.03)',
                border: `1px solid ${currentUrl === LOCAL_DEFAULT_URL ? T.accent : 'rgba(255,255,255,0.08)'}`,
                color: currentUrl === LOCAL_DEFAULT_URL ? '#fff' : T.textDim,
                fontSize: 9.5, fontWeight: 700, cursor: 'pointer', ...mono,
              }}
            >
              Local (7860)
            </button>
            <button
              type="button"
              onClick={() => handleSwitchUrl(HF_DEFAULT_URL)}
              style={{
                flex: 1, padding: '5px 8px', borderRadius: 6,
                background: currentUrl === HF_DEFAULT_URL ? 'rgba(99,102,241,0.25)' : 'rgba(255,255,255,0.03)',
                border: `1px solid ${currentUrl === HF_DEFAULT_URL ? T.accent : 'rgba(255,255,255,0.08)'}`,
                color: currentUrl === HF_DEFAULT_URL ? '#fff' : T.textDim,
                fontSize: 9.5, fontWeight: 700, cursor: 'pointer', ...mono,
              }}
            >
              HuggingFace
            </button>
            <button
              type="button"
              onClick={() => setShowCustomUrl(!showCustomUrl)}
              style={{
                padding: '5px 8px', borderRadius: 6,
                background: showCustomUrl ? 'rgba(99,102,241,0.25)' : 'rgba(255,255,255,0.03)',
                border: '1px solid rgba(255,255,255,0.08)',
                color: T.textMid, fontSize: 9.5, fontWeight: 700, cursor: 'pointer', ...mono,
              }}
            >
              Custom...
            </button>
          </div>

          {showCustomUrl && (
            <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
              <input
                type="text"
                value={customInput}
                onChange={e => setCustomInput(e.target.value)}
                placeholder="http://localhost:8000"
                style={{
                  flex: 1, padding: '4px 8px', borderRadius: 4,
                  background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)',
                  color: '#fff', fontSize: 10, outline: 'none', ...mono,
                }}
              />
              <button
                type="button"
                onClick={() => { if (customInput) handleSwitchUrl(customInput); }}
                style={{
                  padding: '4px 10px', borderRadius: 4, background: T.accent,
                  color: '#fff', border: 'none', fontSize: 10, fontWeight: 700, cursor: 'pointer', ...mono,
                }}
              >
                Set
              </button>
            </div>
          )}
        </div>

        {/* Login Form */}
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label style={{ fontSize: 9, color: T.textMid, letterSpacing: '0.06em', ...mono }}>SECURITY ACCESS CODE</label>
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                style={{ background: 'none', border: 'none', color: T.textDim, fontSize: 9, cursor: 'pointer', ...mono, display: 'flex', alignItems: 'center', gap: 4 }}
              >
                {showPassword ? <EyeOff size={11} /> : <Eye size={11} />}
                {showPassword ? "HIDE" : "SHOW"}
              </button>
            </div>

            <div style={{ position: 'relative' }}>
              <span style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: T.textDim }}>
                <Lock size={13} />
              </span>
              <input
                type={showPassword ? "text" : "password"}
                value={accessCode}
                onChange={e => setAccessCode(e.target.value)}
                placeholder="Enter access code (or 'admin' / 'apex')..."
                disabled={loading}
                style={{
                  width: '100%',
                  background: 'rgba(5, 7, 12, 0.85)',
                  color: T.text,
                  border: `1px solid ${T.borderHi}`,
                  borderRadius: 8,
                  padding: '10px 12px 10px 34px',
                  fontSize: 11.5,
                  outline: 'none',
                  boxSizing: 'border-box',
                  transition: 'border 0.2s',
                  ...mono,
                }}
                onFocus={e => e.target.style.borderColor = T.accent}
                onBlur={e => e.target.style.borderColor = T.borderHi}
              />
            </div>
          </div>

          {error && (
            <div style={{
              padding: '8px 12px',
              background: 'rgba(255, 51, 102, 0.1)',
              border: '1px solid rgba(255, 51, 102, 0.25)',
              borderRadius: 6,
              color: T.red,
              fontSize: 10,
              lineHeight: 1.4,
              ...mono,
            }}>
              ⚠ {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            style={{
              padding: '11px 16px',
              background: loading ? 'rgba(99, 102, 241, 0.3)' : T.accent,
              color: '#fff',
              border: 'none',
              borderRadius: 8,
              fontSize: 11,
              fontWeight: 700,
              cursor: loading ? 'wait' : 'pointer',
              letterSpacing: '0.06em',
              transition: 'all 0.2s',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8,
              ...mono,
            }}
          >
            {loading ? <RefreshCw size={13} className="spin-fast" /> : <Lock size={13} />}
            {loading ? "VERIFYING CHALLENGE..." : "DECRYPT & ENTER TERMINAL"}
          </button>
        </form>

        {/* Divider */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, margin: '2px 0' }}>
          <div style={{ flex: 1, height: 1, background: 'rgba(255,255,255,0.06)' }} />
          <span style={{ fontSize: 9, color: T.textDim, ...mono }}>OR</span>
          <div style={{ flex: 1, height: 1, background: 'rgba(255,255,255,0.06)' }} />
        </div>

        {/* Immediate 1-Click Guest / Offline Entry */}
        <button
          type="button"
          onClick={handleGuestEntry}
          style={{
            padding: '11px 16px',
            background: 'rgba(255, 255, 255, 0.04)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: 8,
            color: T.text,
            fontSize: 11,
            fontWeight: 700,
            cursor: 'pointer',
            letterSpacing: '0.04em',
            transition: 'all 0.2s',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 8,
            ...mono,
          }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = T.green; e.currentTarget.style.color = T.green; }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.1)'; e.currentTarget.style.color = T.text; }}
        >
          <Zap size={13} color={T.green} />
          <span>Launch in Guest / Offline Mode</span>
          <ArrowRight size={13} />
        </button>

      </div>

      <style>{`
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
        .spin-fast { animation: spin 1s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
