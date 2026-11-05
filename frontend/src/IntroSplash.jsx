import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Activity, AlertTriangle, ArrowRight, CheckCircle2, Cpu, Database, Globe2,
  Loader2, RefreshCw, Server, ShieldCheck, Sparkles,
} from 'lucide-react';
import { getApiBaseUrl, setApiBaseUrl } from './api';
import { T } from './theme';

const HF_DEFAULT_URL = 'https://apextrade-core-trade-ai-backend.hf.space';
const LOCAL_DEFAULT_URL = typeof window !== 'undefined' && window.location.hostname === '127.0.0.1'
  ? 'http://127.0.0.1:7860'
  : 'http://localhost:7860';

function StatusRow({ state, children }) {
  const Icon = state === 'ok' ? CheckCircle2 : state === 'warn' ? AlertTriangle : Loader2;
  const color = state === 'ok' ? T.green : state === 'warn' ? '#f5c842' : T.textDim;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 10.5, fontFamily: "'IBM Plex Mono', monospace", color: state === 'ok' ? T.text : T.textMid }}>
      <Icon size={12} color={color} style={state === 'pending' ? { animation: 'spin 1s linear infinite' } : undefined} />
      <span style={{ color }}>{children}</span>
    </div>
  );
}

export default function IntroSplash({ onWokenUp }) {
  const [currentUrl, setCurrentUrl] = useState(() => {
    const configured = getApiBaseUrl();
    if (configured) return configured;
    const isLocal = typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');
    return isLocal ? LOCAL_DEFAULT_URL : HF_DEFAULT_URL;
  });
  const [customInput, setCustomInput] = useState('');
  const [showConfig, setShowConfig] = useState(false);
const [elapsed, setElapsed] = useState(0);
  const [status, setStatus] = useState('connecting');
  const [healthData, setHealthData] = useState(null);
  const [latency, setLatency] = useState(null);
  const [attempts, setAttempts] = useState(0);
  const [retryToken, setRetryToken] = useState(0);
  const [logs, setLogs] = useState([
    'APEXTRADE CORE v4.1 · QUANT BOOT SEQUENCE',
    'Initializing cryptographic security context...',
    'Probing Quant Server /api/health endpoint...',
  ]);
  const maxRetries = 30; // ~75 seconds max

  const finishedRef = useRef(false);
  const onWokenUpRef = useRef(onWokenUp);

  useEffect(() => { onWokenUpRef.current = onWokenUp; }, [onWokenUp]);

  useEffect(() => {
    const timer = setInterval(() => setElapsed(value => value + 1), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (elapsed >= 5 && status !== 'connected') setShowConfig(true);
  }, [elapsed, status]);

  const addLog = useCallback((message) => {
    setLogs(prev => [...prev.slice(-7), message]);
  }, []);

  const finish = useCallback(() => {
    if (finishedRef.current) return;
    finishedRef.current = true;
    onWokenUpRef.current?.();
  }, []);

  useEffect(() => {
    let cancelled = false;
    let timer = null;
    let attempt = 0;
    setStatus('connecting');
    setAttempts(0);

    async function probe() {
      if (cancelled) return;
      attempt += 1;
      setAttempts(attempt);
      const target = currentUrl.replace(/\/$/, '');

      try {
        const startedAt = performance.now();
        const response = await fetch(`${target}/api/health`, {
          method: 'GET',
          headers: { Accept: 'application/json' },
          signal: AbortSignal.timeout(5000),
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        if (cancelled) return;

        const measured = Math.round(performance.now() - startedAt);
        setLatency(data.total_latency_ms ?? measured);
        setHealthData(data);
        setStatus('connected');
        addLog(`[OK] Quant Server connected (${data.total_latency_ms ?? measured}ms)`);
        addLog(`[OK] Storage: ${(data.checks?.database?.type || 'database').toUpperCase()} ${data.checks?.database?.status || 'online'}`);
        addLog(`[OK] AI brain: ${data.checks?.ai_services?.gemini?.status === 'configured' ? 'GEMINI 2.0 FLASH READY' : 'LOCAL FALLBACK ACTIVE'}`);
        addLog('[OK] Simulated feed locked to NSE IST clock');
        timer = setTimeout(finish, 1200);
      } catch (error) {
        if (cancelled) return;
        if (attempt >= maxRetries) {
          setStatus('failed');
          addLog(`[FAIL] Max retries (${maxRetries}) reached. Server unreachable.`);
          setShowConfig(true);
          return;
        }
        if (attempt === 1) addLog(`[WAIT] ${target} unreachable (${error.message})`);
        else if (attempt === 3) addLog('[WAIT] Quant node in cold start · broadcasting wake signals...');
        else if (attempt === 6) addLog('[WAIT] Container boot may take 30-60s on free tier...');
        else if (attempt % 4 === 0) addLog(`[WAIT] Still waiting for quant engine (attempt ${attempt})...`);
        setStatus(attempt > 2 ? 'sleeping' : 'connecting');
        timer = setTimeout(probe, 2500);
      }
    }

    probe();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [addLog, currentUrl, finish, retryToken]);

  const switchTarget = (url) => {
    const clean = (url || '').trim();
    if (!clean) return;
    setApiBaseUrl(clean);
    finishedRef.current = false;
    setCurrentUrl(clean);
    setHealthData(null);
    setLatency(null);
    setAttempts(0);
    setElapsed(0);
    setStatus('connecting');
    setShowConfig(false);
    addLog(`Target re-routed to ${clean}`);
    addLog('Initiating new connection handshake...');
  };

  const retry = () => {
    finishedRef.current = false;
    setHealthData(null);
    setLatency(null);
    setAttempts(0);
    setStatus('connecting');
    addLog('Manual retry requested · re-probing target...');
    setRetryToken(value => value + 1);
  };

  const databaseOk = healthData?.checks?.database?.status === 'healthy';
  const databaseType = (healthData?.checks?.database?.type || 'database').toUpperCase();
  const geminiReady = healthData?.checks?.ai_services?.gemini?.status === 'configured';
  const marketStatus = healthData?.checks?.market?.status;
  const connected = status === 'connected';
  const failed = status === 'failed';

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: T.bg,
      color: T.text,
      fontFamily: "'Inter', -apple-system, sans-serif",
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 999999,
      padding: 24,
      overflow: 'auto',
    }}>
      <div style={{ position: 'absolute', width: '60vw', height: '60vw', background: 'radial-gradient(circle, rgba(99, 102, 241, 0.08) 0%, transparent 65%)', top: '5%', left: '20%', pointerEvents: 'none' }} />
      <div style={{ position: 'absolute', width: '45vw', height: '45vw', background: 'radial-gradient(circle, rgba(0, 245, 160, 0.05) 0%, transparent 70%)', bottom: '10%', right: '15%', pointerEvents: 'none' }} />

      <div style={{
        width: '100%',
        maxWidth: 520,
        background: 'rgba(17, 22, 34, 0.78)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderRadius: 16,
        padding: '30px 28px',
        boxShadow: '0 24px 64px -12px rgba(0, 0, 0, 0.65), 0 0 1px 1px rgba(99, 102, 241, 0.2)',
        display: 'flex',
        flexDirection: 'column',
        gap: 20,
        position: 'relative',
        zIndex: 2,
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 7,
            padding: '4px 12px',
            borderRadius: 999,
            background: 'rgba(99, 102, 241, 0.1)',
            border: '1px solid rgba(99, 102, 241, 0.25)',
            marginBottom: 12,
          }}>
            <Cpu size={14} color={T.accent} />
            <span style={{ fontSize: 10, fontWeight: 700, color: T.accent, letterSpacing: '0.12em' }}>QUANT STATION</span>
          </div>
          <h1 style={{
            fontSize: 24,
            fontWeight: 800,
            letterSpacing: '0.03em',
            margin: 0,
            background: 'linear-gradient(135deg, #ffffff 40%, #d97706 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}>
            ApexTrade AI Engine
          </h1>
          <p style={{ fontSize: 12, color: T.textMid, margin: '4px 0 0' }}>
            Quantitative Algorithmic Trading &amp; AI Copilot
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 16 }}>
          <div style={{ position: 'relative', width: 72, height: 72, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{ position: 'absolute', inset: 0, borderRadius: '50%', border: `1.5px dashed ${connected ? T.green : failed ? T.red : T.accent}40`, animation: 'spin 10s linear infinite' }} />
            <div style={{ position: 'absolute', inset: 9, borderRadius: '50%', border: '2px solid transparent', borderTopColor: connected ? T.green : failed ? T.red : T.accent, borderBottomColor: connected ? T.green : failed ? T.red : T.accentAlt, animation: 'spin 2s cubic-bezier(0.4, 0, 0.2, 1) infinite' }} />
            <div style={{
              width: 38,
              height: 38,
              borderRadius: '50%',
              background: connected ? T.green : failed ? T.red : status === 'sleeping' ? '#f5c842' : T.accent,
              boxShadow: `0 0 26px ${connected ? 'rgba(0,245,160,0.5)' : failed ? 'rgba(255,51,102,0.5)' : status === 'sleeping' ? 'rgba(245,200,66,0.4)' : 'rgba(99,102,241,0.5)'}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#050506',
              transition: 'all 0.4s ease',
            }}>
              {connected ? <CheckCircle2 size={21} strokeWidth={2.5} /> : failed ? <AlertTriangle size={21} strokeWidth={2.5} /> : status === 'sleeping' ? <RefreshCw size={18} strokeWidth={2.5} /> : <Activity size={20} color="#fff" strokeWidth={2.5} />}
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
            <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.06em', color: connected ? T.green : failed ? T.red : status === 'sleeping' ? '#f5c842' : T.accent }}>
              {connected ? 'QUANT SERVER CONNECTED' : failed ? 'CONNECTION FAILED' : status === 'sleeping' ? 'WAKING UP SERVER' : 'HANDSHAKE IN PROGRESS'}
              <span style={{ fontSize: 10, color: T.textDim, marginLeft: 6 }}>({elapsed}s)</span>
            </div>
            <div style={{ fontSize: 10, color: T.textDim, fontFamily: "'IBM Plex Mono', monospace" }}>
              attempt {attempts || 1} · latency {latency != null ? `${latency}ms` : '--'}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: '12px 14px', background: 'rgba(7, 9, 14, 0.5)', borderRadius: 10, border: '1px solid rgba(255, 255, 255, 0.05)' }}>
          <StatusRow state={connected ? 'ok' : failed ? 'error' : status === 'sleeping' ? 'warn' : 'pending'}>
            {connected ? `Quant Server Engine: CONNECTED (${latency ?? healthData?.total_latency_ms ?? 0}ms)` : failed ? 'Quant Server Engine: UNREACHABLE' : 'Quant Server Engine: CONNECTING...'}
          </StatusRow>
          <StatusRow state={connected ? (databaseOk ? 'ok' : 'warn') : failed ? 'error' : 'pending'}>
            {connected ? `Storage Engine: ${databaseType} ${databaseOk ? 'ONLINE' : 'DEGRADED'}` : failed ? 'Storage Engine: UNREACHABLE' : 'Storage Engine: WAITING'}
          </StatusRow>
          <StatusRow state={connected ? (geminiReady ? 'ok' : 'warn') : failed ? 'error' : 'pending'}>
            {connected ? `AI Brain: ${geminiReady ? 'GEMINI 2.0 FLASH READY' : 'LOCAL FALLBACK ACTIVE'}` : failed ? 'AI Brain: UNREACHABLE' : 'AI Brain: WAITING'}
          </StatusRow>
          <StatusRow state={connected ? 'ok' : failed ? 'error' : 'pending'}>
            {connected ? `Market Feed: SIMULATED · locked to NSE IST clock · ${marketStatus ? marketStatus.toUpperCase() : 'UNKNOWN'}` : failed ? 'Market Feed: UNREACHABLE' : 'Market Feed: WAITING'}
          </StatusRow>
        </div>

        <div style={{
          height: 108,
          background: 'rgba(7, 9, 14, 0.85)',
          borderRadius: 8,
          border: '1px solid rgba(255, 255, 255, 0.08)',
          padding: '10px 14px',
          display: 'flex',
          flexDirection: 'column',
          gap: 5,
          overflowY: 'auto',
          fontSize: 10,
          fontFamily: "'IBM Plex Mono', monospace",
        }}>
          {logs.map((log, index) => (
            <div key={`${index}-${log.slice(0, 12)}`} style={{
              color: index === logs.length - 1 ? (connected ? T.green : T.blue) : T.textDim,
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}>
              {log}
            </div>
          ))}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={() => switchTarget(LOCAL_DEFAULT_URL)} style={{
              flex: 1,
              padding: '8px 10px',
              borderRadius: 8,
              background: currentUrl === LOCAL_DEFAULT_URL ? 'rgba(99, 102, 241, 0.2)' : 'rgba(255, 255, 255, 0.04)',
              border: `1px solid ${currentUrl === LOCAL_DEFAULT_URL ? T.accent : 'rgba(255, 255, 255, 0.08)'}`,
              color: currentUrl === LOCAL_DEFAULT_URL ? '#fff' : T.textMid,
              fontSize: 11,
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 5,
            }}>
              <Server size={12} /> Local (7860)
            </button>
            <button onClick={() => switchTarget(HF_DEFAULT_URL)} style={{
              flex: 1,
              padding: '8px 10px',
              borderRadius: 8,
              background: currentUrl === HF_DEFAULT_URL ? 'rgba(99, 102, 241, 0.2)' : 'rgba(255, 255, 255, 0.04)',
              border: `1px solid ${currentUrl === HF_DEFAULT_URL ? T.accent : 'rgba(255, 255, 255, 0.08)'}`,
              color: currentUrl === HF_DEFAULT_URL ? '#fff' : T.textMid,
              fontSize: 11,
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 5,
            }}>
              <Globe2 size={12} /> HuggingFace
            </button>
            <button onClick={() => setShowConfig(value => !value)} style={{
              padding: '8px 12px',
              borderRadius: 8,
              background: showConfig ? 'rgba(99, 102, 241, 0.25)' : 'rgba(255, 255, 255, 0.04)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              color: T.textMid,
              fontSize: 11,
              fontWeight: 600,
              cursor: 'pointer',
            }}>
              Custom
            </button>
          </div>

          <div style={{ fontSize: 10, color: T.textDim, textAlign: 'center', wordBreak: 'break-all' }}>
            Target: <span style={{ color: T.blue }}>{currentUrl}</span>
          </div>

          {status === 'sleeping' && !showConfig && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 10.5, color: '#f5c842', lineHeight: 1.5 }}>
              <AlertTriangle size={13} />
              Free-tier containers sleep when idle. Cold start usually takes 30-50s.
            </div>
          )}

          {showConfig && (
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 1,
              padding: 12,
              background: 'rgba(0, 0, 0, 0.32)',
              borderRadius: 10,
              border: `1px solid ${status === 'connected' ? T.border : T.borderHi}`,
            }}>
              {status !== 'connected' && (
                <div style={{ fontSize: 10, color: T.textMid, marginBottom: 8, lineHeight: 1.5 }}>
                  Quant server not reachable after 5 seconds. Point the terminal at a local, Cloud Run, or Hugging Face backend, retry, or continue offline.
                </div>
              )}
              <div style={{ display: 'flex', gap: 8 }}>
                <input
                  type="text"
                  value={customInput}
                  onChange={event => setCustomInput(event.target.value)}
                  placeholder="https://my-backend.hf.space"
                  style={{
                    flex: 1,
                    background: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    borderRadius: 6,
                    padding: '7px 10px',
                    color: '#fff',
                    fontSize: 11,
                    outline: 'none',
                  }}
                />
                <button
                  onClick={() => customInput && switchTarget(customInput)}
                  style={{ padding: '7px 14px', borderRadius: 6, background: T.accent, color: '#fff', border: 'none', fontSize: 11, fontWeight: 600, cursor: 'pointer' }}
                >
                  Connect
                </button>
                <button
                  onClick={retry}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 5,
                    padding: '7px 12px',
                    borderRadius: 6,
                    background: 'rgba(255, 255, 255, 0.05)',
                    color: T.text,
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    fontSize: 11,
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  <RefreshCw size={12} /> Retry
                </button>
              </div>
            </div>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: 10, borderTop: '1px solid rgba(255,255,255,0.06)' }}>
          <span style={{ fontSize: 10.5, color: T.textDim, display: 'flex', alignItems: 'center', gap: 4 }}>
            <ShieldCheck size={13} color={T.green} /> Enterprise Guard Active
          </span>
          <button
            onClick={finish}
            style={{
              background: 'transparent',
              border: '1px solid rgba(255,255,255,0.12)',
              borderRadius: 6,
              color: T.text,
              padding: '7px 14px',
              fontSize: 11,
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              transition: 'all 0.2s',
            }}
            onMouseEnter={event => { event.currentTarget.style.borderColor = T.accent; }}
            onMouseLeave={event => { event.currentTarget.style.borderColor = 'rgba(255,255,255,0.12)'; }}
          >
            {connected ? <Sparkles size={12} /> : failed ? <AlertTriangle size={12} /> : <ArrowRight size={12} />}
            {connected ? 'Enter Terminal' : failed ? 'Enter Terminal (Offline Demo Mode)' : 'Enter Terminal (Offline Demo Mode)'}
          </button>
        </div>
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes pulse { 0%,100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.5; transform: scale(0.85); } }
      `}</style>
    </div>
  );
}
