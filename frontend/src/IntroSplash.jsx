import { API_BASE_URL } from './api';
import React, { useState, useEffect } from 'react';

const T = {
  bg:         '#05070c',
  panel:      '#0d1017',
  border:     '#161b26',
  text:       '#d0d8ed',
  textMid:    '#6e7a96',
  textDim:    '#363d55',
  accent:     '#7b6cff',
  accentAlt:  '#9b5de5',
  green:      '#00e5a8',
  blue:       '#4da6ff',
  gold:       '#f5c842',
};

const LOG_MESSAGES = [
  "✦ APEXTRADE CORE v3.14 — INITIALIZING BOOT SEQUENCE",
  "✦ Setting up local cryptographic security context...",
  "✦ Searching for active Render cloud backend nodes...",
  "✦ Cloud server detected (Render free tier). Waking up node...",
  "✦ Handshake ping sent. Waiting for database spin-up...",
  "✦ Handshake ping sent. Waiting for database spin-up...",
  "✦ Database thread waking up. Preparing cache storage...",
  "✦ Initializing multi-timeframe confirmation scanning models...",
  "✦ Loading Candlestick Bible pattern matcher configurations...",
  "✦ Connecting websocket stream pipelines to NSE ticker tape...",
  "✦ Handshake successful! Opening terminal interface..."
];

export default function IntroSplash({ onWokenUp }) {
  const [elapsed, setElapsed] = useState(0);
  const [logs, setLogs] = useState([]);
  const [logIndex, setLogIndex] = useState(0);
  const [statusText, setStatusText] = useState("CONNECTING TO CLOUD NODE...");
  const [isDone, setIsDone] = useState(false);

  const BASE_URL = API_BASE_URL;

  // Increment elapsed timer
  useEffect(() => {
    const t = setInterval(() => setElapsed(e => e + 1), 1000);
    return () => clearInterval(t);
  }, []);

  // Append logs sequentially to simulate boot
  useEffect(() => {
    if (logIndex < LOG_MESSAGES.length - 1 && !isDone) {
      const delay = logIndex === 0 ? 500 : logIndex === 3 ? 4000 : logIndex === 4 || logIndex === 5 ? 5000 : 1500;
      const t = setTimeout(() => {
        setLogs(prev => [...prev, LOG_MESSAGES[logIndex]]);
        setLogIndex(l => l + 1);
      }, delay);
      return () => clearTimeout(t);
    }
  }, [logIndex, isDone]);

  // Keep latest onWokenUp callback in a ref to avoid resetting the ping effect
  const onWokenUpRef = React.useRef(onWokenUp);
  useEffect(() => {
    onWokenUpRef.current = onWokenUp;
  }, [onWokenUp]);

  // Ping backend to wake it up
  useEffect(() => {
    let active = true;
    let failCount = 0;

    async function ping() {
      if (!active) return;
      try {
        const res = await fetch(`${BASE_URL}/`);
        if (res.ok) {
          const data = await res.json();
          if (data.status === "ok") {
            // Success! Woken up
            setIsDone(true);
            setStatusText("ESTABLISHED CONNECTION");
            setLogs(prev => [
              ...prev,
              "✦ Connection response received successfully from cloud node.",
              "✦ Handshake confirmed. Redirecting to trading terminal..."
            ]);
            setTimeout(() => {
              if (active) onWokenUpRef.current();
            }, 1800);
            return;
          }
        }
      } catch (e) {
        failCount++;
        // Speed up logs if server takes longer to wake up
        setLogIndex(prev => {
          if (failCount > 3 && prev < 6) {
            return Math.min(6, prev + 1);
          }
          return prev;
        });
      }
      
      // Ping again in 2 seconds
      setTimeout(ping, 2000);
    }

    // Add first logs
    setLogs([LOG_MESSAGES[0]]);
    setLogIndex(1);
    
    // Start pinging after a short delay
    const startDelay = setTimeout(ping, 1000);

    return () => {
      active = false;
      clearTimeout(startDelay);
    };
  }, []);

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: T.bg,
      color: T.text,
      fontFamily: "'Inter', sans-serif",
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 99999,
      padding: '24px',
      overflow: 'hidden',
    }}>
      {/* Dynamic glow overlays */}
      <div style={{
        position: 'absolute',
        width: '50vw',
        height: '50vw',
        background: `radial-gradient(circle, rgba(123, 108, 255, 0.08) 0%, transparent 70%)`,
        top: '10%',
        left: '15%',
        pointerEvents: 'none',
      }} />
      <div style={{
        position: 'absolute',
        width: '40vw',
        height: '40vw',
        background: `radial-gradient(circle, rgba(0, 229, 168, 0.05) 0%, transparent 75%)`,
        bottom: '10%',
        right: '15%',
        pointerEvents: 'none',
      }} />

      {/* Main Container */}
      <div style={{
        width: '100%',
        maxWidth: '460px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 28,
        animation: 'fadeIn 0.6s ease',
      }}>
        {/* Branding Logo */}
        <div style={{ textAlign: 'center' }}>
          <div style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: 22,
            fontWeight: 800,
            letterSpacing: '0.18em',
            background: `linear-gradient(135deg, ${T.accent}, ${T.accentAlt})`,
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            marginBottom: 8,
          }}>
            ◈ APEXTRADE
          </div>
          <div style={{
            fontSize: 8.5,
            fontWeight: 700,
            letterSpacing: '0.22em',
            color: T.textMid,
            fontFamily: "'IBM Plex Mono', monospace",
          }}>
            QUANT QUANTUM INTELLIGENCE TERMINAL
          </div>
        </div>

        {/* Orbit / Pulse Animation */}
        <div style={{
          position: 'relative',
          width: '100px',
          height: '100px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          {/* Outer Ring */}
          <div style={{
            position: 'absolute',
            inset: 0,
            borderRadius: '50%',
            border: `1.5px dashed ${isDone ? T.green : T.accent}40`,
            animation: 'spin 12s linear infinite',
          }} />
          {/* Middle Ring */}
          <div style={{
            position: 'absolute',
            inset: 12,
            borderRadius: '50%',
            border: `2px solid transparent`,
            borderTopColor: isDone ? T.green : T.accent,
            borderBottomColor: isDone ? T.green : T.accentAlt,
            animation: 'spin 2.5s cubic-bezier(0.53, 0.21, 0.29, 0.67) infinite',
          }} />
          {/* Inner Glowing Core */}
          <div style={{
            width: '44px',
            height: '44px',
            borderRadius: '50%',
            background: isDone ? T.green : T.accent,
            boxShadow: `0 0 24px ${isDone ? T.green : T.accent}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 16,
            animation: 'pulse 2s infinite ease-in-out',
            color: '#fff',
            fontWeight: 700,
          }}>
            {isDone ? '✓' : '◈'}
          </div>
        </div>

        {/* Status indicator */}
        <div style={{ textAlign: 'center', width: '100%' }}>
          <div style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: 10,
            fontWeight: 700,
            letterSpacing: '0.08em',
            color: isDone ? T.green : T.gold,
            marginBottom: 6,
          }}>
            {statusText} ({elapsed}s)
          </div>
          <div style={{
            fontSize: 9.5,
            color: T.textMid,
            lineHeight: 1.6,
            maxWidth: '360px',
            margin: '0 auto',
          }}>
            {!isDone 
              ? "Waking up the cloud server on Render. This takes up to 45 seconds during backend cold starts."
              : "Handshake verified. Decrypting environment context..."}
          </div>
        </div>

        {/* Micro terminal logger window */}
        <div style={{
          width: '100%',
          height: '140px',
          background: 'rgba(17, 21, 32, 0.7)',
          backdropFilter: 'blur(8px)',
          border: '1px solid rgba(123, 108, 255, 0.25)',
          borderRadius: 8,
          padding: '12px 14px',
          display: 'flex',
          flexDirection: 'column',
          gap: 6,
          overflowY: 'auto',
          boxSizing: 'border-box',
          scrollbarWidth: 'none',
        }}>
          {logs.map((log, index) => {
            const isLast = index === logs.length - 1;
            return (
              <div 
                key={index} 
                style={{
                  fontFamily: "'IBM Plex Mono', monospace",
                  fontSize: 9,
                  lineHeight: 1.4,
                  color: isLast ? (isDone ? T.green : T.blue) : T.textDim,
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  animation: 'fadeIn 0.2s ease',
                }}
              >
                {log}
              </div>
            );
          })}
        </div>
      </div>

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        @keyframes pulse {
          0%, 100% { transform: scale(1); opacity: 1; }
          50% { transform: scale(0.9); opacity: 0.8; }
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}
