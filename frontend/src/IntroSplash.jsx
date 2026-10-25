import React, { useState, useEffect, useRef } from 'react';
import { getApiBaseUrl, setApiBaseUrl } from './api';
import { Activity, Server, Database, Cpu, Wifi, WifiOff, RefreshCw, ArrowRight, CheckCircle2, AlertTriangle, ShieldCheck } from 'lucide-react';

const T = {
  bg: '#07090e',
  surface: '#0d111a',
  panel: '#111622',
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

const HF_DEFAULT_URL = "https://apextrade-core-trade-ai-backend.hf.space";
const LOCAL_DEFAULT_URL = "http://localhost:7860";

export default function IntroSplash({ onWokenUp }) {
  const [currentUrl, setCurrentUrl] = useState(() => getApiBaseUrl() || (window.location.hostname === 'localhost' ? LOCAL_DEFAULT_URL : HF_DEFAULT_URL));
  const [customInput, setCustomInput] = useState('');
  const [showConfig, setShowConfig] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [status, setStatus] = useState('connecting'); // 'connecting' | 'connected' | 'sleeping' | 'error'
  const [healthData, setHealthData] = useState(null);
  const [logs, setLogs] = useState([
    "✦ APEXTRADE CORE v3.15 — QUANT BOOT SEQUENCE",
    "✦ Initializing cryptographic security context...",
    "✦ Probing Quant Engine API endpoint...",
  ]);

  const onWokenUpRef = useRef(onWokenUp);
  useEffect(() => {
    onWokenUpRef.current = onWokenUp;
  }, [onWokenUp]);

  // Elapsed second counter
  useEffect(() => {
    const timer = setInterval(() => setElapsed(e => e + 1), 1000);
    return () => clearInterval(timer);
  }, []);

  // Ping engine loop
  useEffect(() => {
    let isCancelled = false;
    let attempt = 0;

    const addLog = (msg) => {
      if (isCancelled) return;
      setLogs(prev => [...prev.slice(-7), msg]);
    };

    async function probeServer() {
      if (isCancelled) return;
      attempt++;
      const target = currentUrl.replace(/\/$/, "");

      try {
        const startTime = performance.now();
        const res = await fetch(`${target}/api/health`, { method: 'GET', signal: AbortSignal.timeout(6000) })
          .catch(() => fetch(`${target}/`, { method: 'GET', signal: AbortSignal.timeout(6000) }));

        if (!res || !res.ok) {
          throw new Error(`HTTP ${res ? res.status : 'No Response'}`);
        }

        const data = await res.json();
        const latency = Math.round(performance.now() - startTime);

        if (!isCancelled) {
          setStatus('connected');
          setHealthData({ ...data, latency });
          addLog(`✦ [✓] Handshake confirmed with Quant Engine (${latency}ms)`);
          addLog(`✦ [✓] AI Brain: Gemini 2.0 Flash verified`);
          addLog(`✦ [✓] Initializing quantitative terminal interface...`);

          setTimeout(() => {
            if (!isCancelled) onWokenUpRef.current();
          }, 1200);
          return;
        }
      } catch (err) {
        if (isCancelled) return;
        if (attempt > 2) {
          setStatus('sleeping');
        }
        if (attempt === 3) {
          addLog(`✦ Node in sleep state (cold start). Broadcasting wake signals...`);
        } else if (attempt === 6) {
          addLog(`✦ Container booting. Hugging Face free tier takes 30-60s to warm up.`);
        } else if (attempt % 5 === 0) {
          addLog(`✦ Waiting for quant engine readiness (attempt ${attempt})...`);
        }
      }

      // Continuous retry every 2.5s
      if (!isCancelled) {
        setTimeout(probeServer, 2500);
      }
    }

    probeServer();

    return () => {
      isCancelled = true;
    };
  }, [currentUrl]);

  const handleSwitchUrl = (newUrl) => {
    const clean = (newUrl || '').trim();
    if (!clean) return;
    setApiBaseUrl(clean);
    setCurrentUrl(clean);
    setStatus('connecting');
    setLogs(prev => [
      ...prev.slice(-4),
      `✦ Target re-routed to: ${clean}`,
      `✦ Initiating new connection handshake...`
    ]);
  };

  const handleProceedOffline = () => {
    onWokenUpRef.current();
  };

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: T.bg,
      color: T.text,
      fontFamily: "'Inter', -apple-system, sans-serif",
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 999999,
      padding: '24px',
      overflow: 'hidden',
    }}>
      {/* Background ambient radial gradients */}
      <div style={{
        position: 'absolute',
        width: '60vw',
        height: '60vw',
        background: `radial-gradient(circle, rgba(99, 102, 241, 0.08) 0%, transparent 65%)`,
        top: '5%',
        left: '20%',
        pointerEvents: 'none',
      }} />
      <div style={{
        position: 'absolute',
        width: '45vw',
        height: '45vw',
        background: `radial-gradient(circle, rgba(0, 245, 160, 0.05) 0%, transparent 70%)`,
        bottom: '10%',
        right: '15%',
        pointerEvents: 'none',
      }} />

      {/* Main Glassmorphic Card */}
      <div style={{
        width: '100%',
        maxWidth: 480,
        background: 'rgba(17, 22, 34, 0.75)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderRadius: 16,
        padding: '32px 28px',
        boxShadow: '0 24px 64px -12px rgba(0, 0, 0, 0.65), 0 0 1px 1px rgba(99, 102, 241, 0.2)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 24,
        position: 'relative',
        zIndex: 2,
      }}>

        {/* Brand Header */}
        <div style={{ textAlign: 'center' }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 8,
            padding: '4px 12px',
            borderRadius: 999,
            background: 'rgba(99, 102, 241, 0.1)',
            border: '1px solid rgba(99, 102, 241, 0.25)',
            marginBottom: 12,
          }}>
            <Cpu size={14} color={T.accent} />
            <span style={{ fontSize: 11, fontWeight: 700, color: T.accent, letterSpacing: '0.12em' }}>QUANT STATION</span>
          </div>

          <h1 style={{
            fontSize: 24,
            fontWeight: 800,
            letterSpacing: '0.04em',
            margin: 0,
            background: `linear-gradient(135deg, #ffffff 40%, ${T.accentAlt} 100%)`,
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}>
            ApexTrade AI Engine
          </h1>
          <p style={{ fontSize: 12, color: T.textMid, marginTop: 4, margin: '4px 0 0' }}>
            Quantitative Algorithmic Trading & AI Copilot
          </p>
        </div>

        {/* Pulse / Radar Orb */}
        <div style={{ position: 'relative', width: 90, height: 90, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          {/* Rotating outer ring */}
          <div style={{
            position: 'absolute',
            inset: 0,
            borderRadius: '50%',
            border: `1.5px dashed ${status === 'connected' ? T.green : T.accent}40`,
            animation: 'spin 10s linear infinite',
          }} />
          {/* Inner pulsing ring */}
          <div style={{
            position: 'absolute',
            inset: 10,
            borderRadius: '50%',
            border: `2px solid transparent`,
            borderTopColor: status === 'connected' ? T.green : T.accent,
            borderBottomColor: status === 'connected' ? T.green : T.accentAlt,
            animation: 'spin 2s cubic-bezier(0.4, 0, 0.2, 1) infinite',
          }} />
          {/* Core icon */}
          <div style={{
            width: 44,
            height: 44,
            borderRadius: '50%',
            background: status === 'connected' ? T.green : status === 'sleeping' ? T.gold : T.accent,
            boxShadow: `0 0 28px ${status === 'connected' ? 'rgba(0,245,160,0.5)' : status === 'sleeping' ? 'rgba(251,191,36,0.4)' : 'rgba(99,102,241,0.5)'}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#07090e',
            transition: 'all 0.4s ease',
          }}>
            {status === 'connected' ? (
              <CheckCircle2 size={24} color="#07090e" strokeWidth={2.5} />
            ) : status === 'sleeping' ? (
              <RefreshCw size={20} color="#07090e" className="spin-fast" strokeWidth={2.5} />
            ) : (
              <Activity size={22} color="#ffffff" strokeWidth={2.5} />
            )}
          </div>
        </div>

        {/* Status Text & Target */}
        <div style={{ textAlign: 'center', width: '100%' }}>
          <div style={{
            fontSize: 12,
            fontWeight: 700,
            letterSpacing: '0.06em',
            color: status === 'connected' ? T.green : status === 'sleeping' ? T.gold : T.accent,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 6,
          }}>
            {status === 'connected' ? 'QUANT SERVER CONNECTED' : status === 'sleeping' ? 'WAKING UP SERVER...' : 'HANDSHAKE IN PROGRESS...'}
            <span style={{ fontSize: 11, color: T.textDim }}>({elapsed}s)</span>
          </div>

          <div style={{
            fontSize: 11,
            color: T.textMid,
            marginTop: 6,
            wordBreak: 'break-all',
            padding: '4px 10px',
            background: 'rgba(0,0,0,0.25)',
            borderRadius: 6,
            border: '1px solid rgba(255,255,255,0.05)',
            display: 'inline-block',
          }}>
            Target: <code style={{ color: T.blue }}>{currentUrl}</code>
          </div>

          {status === 'sleeping' && (
            <p style={{ fontSize: 11, color: T.gold, marginTop: 8, lineHeight: 1.5 }}>
              ⚡ Hugging Face free containers sleep when idle. Cold start typically takes 30-50s. Please wait or switch target below.
            </p>
          )}
        </div>

        {/* Terminal Live Diagnostics Box */}
        <div style={{
          width: '100%',
          height: 120,
          background: 'rgba(7, 9, 14, 0.85)',
          borderRadius: 8,
          border: '1px solid rgba(255, 255, 255, 0.08)',
          padding: '10px 14px',
          display: 'flex',
          flexDirection: 'column',
          gap: 6,
          overflowY: 'auto',
          fontSize: 11,
          fontFamily: "'JetBrains Mono', 'IBM Plex Mono', monospace",
        }}>
          {logs.map((log, i) => (
            <div key={i} style={{
              color: i === logs.length - 1 ? (status === 'connected' ? T.green : T.blue) : T.textDim,
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}>
              {log}
            </div>
          ))}
        </div>

        {/* Server Target Switcher Toolbar */}
        <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ display: 'flex', gap: 8, width: '100%' }}>
            <button
              onClick={() => handleSwitchUrl(LOCAL_DEFAULT_URL)}
              style={{
                flex: 1,
                padding: '8px 10px',
                borderRadius: 8,
                background: currentUrl === LOCAL_DEFAULT_URL ? 'rgba(99,102,241,0.2)' : 'rgba(255,255,255,0.04)',
                border: `1px solid ${currentUrl === LOCAL_DEFAULT_URL ? T.accent : 'rgba(255,255,255,0.08)'}`,
                color: currentUrl === LOCAL_DEFAULT_URL ? '#fff' : T.textMid,
                fontSize: 11,
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 5,
              }}
            >
              <Server size={12} /> Local (7860)
            </button>

            <button
              onClick={() => handleSwitchUrl(HF_DEFAULT_URL)}
              style={{
                flex: 1,
                padding: '8px 10px',
                borderRadius: 8,
                background: currentUrl === HF_DEFAULT_URL ? 'rgba(99,102,241,0.2)' : 'rgba(255,255,255,0.04)',
                border: `1px solid ${currentUrl === HF_DEFAULT_URL ? T.accent : 'rgba(255,255,255,0.08)'}`,
                color: currentUrl === HF_DEFAULT_URL ? '#fff' : T.textMid,
                fontSize: 11,
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 5,
              }}
            >
              <Activity size={12} /> HuggingFace
            </button>

            <button
              onClick={() => setShowConfig(!showConfig)}
              style={{
                padding: '8px 12px',
                borderRadius: 8,
                background: showConfig ? 'rgba(99,102,241,0.25)' : 'rgba(255,255,255,0.04)',
                border: '1px solid rgba(255,255,255,0.08)',
                color: T.textMid,
                fontSize: 11,
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Custom...
            </button>
          </div>

          {/* Custom URL Input Accordion */}
          {showConfig && (
            <div style={{
              display: 'flex',
              gap: 8,
              padding: 10,
              background: 'rgba(0,0,0,0.3)',
              borderRadius: 8,
              border: '1px solid rgba(255,255,255,0.08)',
            }}>
              <input
                type="text"
                value={customInput}
                onChange={e => setCustomInput(e.target.value)}
                placeholder="https://my-backend.hf.space"
                style={{
                  flex: 1,
                  background: 'rgba(255,255,255,0.05)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: 6,
                  padding: '6px 10px',
                  color: '#fff',
                  fontSize: 11,
                  outline: 'none',
                }}
              />
              <button
                onClick={() => {
                  if (customInput) handleSwitchUrl(customInput);
                }}
                style={{
                  padding: '6px 14px',
                  borderRadius: 6,
                  background: T.accent,
                  color: '#fff',
                  border: 'none',
                  fontSize: 11,
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Connect
              </button>
            </div>
          )}
        </div>

        {/* Bottom Actions: Offline Launch Escape Hatch */}
        <div style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: 8, borderTop: '1px solid rgba(255,255,255,0.06)' }}>
          <span style={{ fontSize: 11, color: T.textDim, display: 'flex', alignItems: 'center', gap: 4 }}>
            <ShieldCheck size={13} color={T.green} /> Enterprise Guard Active
          </span>

          <button
            onClick={handleProceedOffline}
            style={{
              background: 'transparent',
              border: '1px solid rgba(255,255,255,0.12)',
              borderRadius: 6,
              color: T.text,
              padding: '6px 14px',
              fontSize: 11,
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              transition: 'all 0.2s',
            }}
            onMouseEnter={e => e.currentTarget.style.borderColor = T.accent}
            onMouseLeave={e => e.currentTarget.style.borderColor = 'rgba(255,255,255,0.12)'}
          >
            Launch Terminal <ArrowRight size={12} />
          </button>
        </div>

      </div>

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        .spin-fast {
          animation: spin 1.2s linear infinite;
        }
      `}</style>
    </div>
  );
}
