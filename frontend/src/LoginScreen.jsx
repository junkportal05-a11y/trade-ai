import { API_BASE_URL } from './api';
import React, { useState } from 'react';

function getTimeoutSignal(ms) {
  if (typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function') {
    return AbortSignal.timeout(ms);
  }
  const controller = new AbortController();
  setTimeout(() => controller.abort(), ms);
  return controller.signal;
}

const T = {
  bg:         '#05070c',
  panel:      '#0d1017',
  panelAlt:   '#111520',
  border:     '#161b26',
  borderHi:   '#252c40',
  text:       '#d0d8ed',
  textMid:    '#6e7a96',
  textDim:    '#363d55',
  accent:     '#7b6cff',
  accentAlt:  '#9b5de5',
  green:      '#00e5a8',
  red:        '#ff3d5a',
};

const mono = { fontFamily: "'IBM Plex Mono', monospace" };

export default function LoginScreen({ onLogin }) {
  const [accessCode, setAccessCode] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const BASE_URL = API_BASE_URL;
  const [serverReady, setServerReady] = useState(false);
  const [waking, setWaking] = useState(true);

  // Pre-warm the backend on mount (HF Spaces auto-sleep after inactivity)
  React.useEffect(() => {
    let cancelled = false;
    const wake = async () => {
      for (let i = 0; i < 5; i++) {
        try {
          // Use mode: 'no-cors' to bypass CORS blocks on raw waker hit
          const r = await fetch(BASE_URL + "/", { 
            method: "GET", 
            mode: "no-cors",
            signal: getTimeoutSignal(10000) 
          });
          // Any non-throwing response (including opaque 0) means server is active and reachable
          if (r && !cancelled) { 
            setServerReady(true); 
            setWaking(false); 
            return; 
          }
        } catch (_) { /* server still waking */ }
        if (!cancelled) await new Promise(ok => setTimeout(ok, 2000 * (i + 1)));
      }
      if (!cancelled) { setServerReady(false); setWaking(false); }
    };
    wake();
    return () => { cancelled = true; };
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    const code = accessCode.trim();
    if (!code) {
      setError("Please enter your security access code.");
      return;
    }

    setLoading(true);

    const MAX_RETRIES = 3;
    const payload = JSON.stringify({ username: "code", password: code });

    for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
      try {
        const res = await fetch(`${BASE_URL}/api/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: payload,
          signal: getTimeoutSignal(15000),
        });
        
        if (!res.ok) {
          let errMessage = "AUTHENTICATION FAILED: Invalid access code.";
          try {
            const errData = await res.json();
            if (errData && errData.detail) errMessage = "ERROR: " + errData.detail;
          } catch (_) {}
          // Auth errors are not retryable — break immediately
          setError(errMessage);
          setLoading(false);
          return;
        }
        
        const data = await res.json();
        
        // Store a flag indicating we are logged in (actual token is in HttpOnly cookie)
        localStorage.setItem('is_logged_in', 'true');
        
        // Also store session token if provided (fallback for non-cookie auth)
        if (data.token) sessionStorage.setItem('apt_token', data.token);
        
        // Propagate user metadata to parent App component
        onLogin(data.username, data.role, data.clearance);
        return; // success — exit
      } catch (err) {
        const isNetworkError = err.name === "TypeError" || err.name === "AbortError" || (err.message && err.message.toLowerCase().includes("failed to fetch"));
        if (isNetworkError && attempt < MAX_RETRIES) {
          // Server likely sleeping — wait and retry
          setError(`SERVER WAKING UP — Retry ${attempt}/${MAX_RETRIES}...`);
          await new Promise(ok => setTimeout(ok, 3000 * attempt));
          continue;
        }
        // Final attempt or non-network error
        setError(
          isNetworkError
            ? "CONNECTION FAILED: Server is unreachable. It may be starting up — please wait 30 seconds and try again."
            : (err.message || "AUTHENTICATION FAILED: Connection error.")
        );
        setLoading(false);
        return;
      }
    }
  };


  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: T.bg,
      color: T.text,
      fontFamily: "'Inter', sans-serif",
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 999999,
      padding: '20px',
      overflow: 'hidden',
    }}>
      {/* Background ambient radial gradients */}
      <div style={{
        position: 'absolute',
        width: '60vw',
        height: '60vw',
        background: `radial-gradient(circle, rgba(123, 108, 255, 0.07) 0%, transparent 70%)`,
        top: '-10%',
        left: '-10%',
        pointerEvents: 'none',
      }} />
      <div style={{
        position: 'absolute',
        width: '50vw',
        height: '50vw',
        background: `radial-gradient(circle, rgba(0, 229, 168, 0.04) 0%, transparent 75%)`,
        bottom: '-10%',
        right: '-10%',
        pointerEvents: 'none',
      }} />

      {/* Login Card */}
      <div style={{
        width: '100%',
        maxWidth: '380px',
        background: 'rgba(13, 16, 23, 0.65)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        border: '1px solid rgba(123, 108, 255, 0.35)',
        borderRadius: 16,
        padding: '30px 24px',
        boxShadow: '0 24px 48px rgba(0,0,0,0.6), 0 0 32px rgba(123, 108, 255, 0.15), inset 0 1px 0 rgba(255,255,255,0.05)',
        display: 'flex',
        flexDirection: 'column',
        gap: 24,
        animation: 'fadeIn 0.5s ease',
      }}>
        {/* Terminal Header Decoration */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: `1px solid ${T.border}`, paddingBottom: 12 }}>
          <div style={{ display: 'flex', gap: 6 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: T.red }} />
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#f5c842' }} />
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: T.green }} />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{
              width: 6, height: 6, borderRadius: '50%',
              background: waking ? '#f5c842' : serverReady ? T.green : T.red,
              boxShadow: waking ? '0 0 6px #f5c842' : serverReady ? `0 0 6px ${T.green}` : `0 0 6px ${T.red}`,
              animation: waking ? 'pulse 1.2s ease-in-out infinite' : 'none',
            }} />
            <span style={{ fontSize: 7.5, color: T.textDim, letterSpacing: '0.15em', ...mono }}>
              {waking ? 'CONNECTING...' : serverReady ? 'SERVER ONLINE' : 'SERVER OFFLINE'}
            </span>
          </div>
        </div>

        {/* Branding Logo */}
        <div style={{ textAlign: 'center' }}>
          <div style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: 20,
            fontWeight: 800,
            letterSpacing: '0.15em',
            background: `linear-gradient(135deg, ${T.accent}, ${T.accentAlt})`,
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            marginBottom: 6,
          }}>
            ◈ APEXTRADE
          </div>
          <div style={{
            fontSize: 8.5,
            fontWeight: 700,
            letterSpacing: '0.12em',
            color: T.textMid,
            ...mono,
          }}>
            RESTRICTED ACCESS TERMINAL
          </div>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Single Access Code Input */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label style={{ fontSize: 8.5, color: T.textMid, letterSpacing: '0.08em', ...mono }}>ENTER ACCESS SECURITY CODE</label>
              <button 
                type="button" 
                onClick={() => setShowPassword(!showPassword)}
                style={{ background: 'none', border: 'none', color: T.textDim, fontSize: 8, cursor: 'pointer', ...mono, outline: 'none' }}
              >
                {showPassword ? "HIDE" : "SHOW"}
              </button>
            </div>
            <div style={{ position: 'relative' }}>
              <span style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: T.textDim, fontSize: 12 }}>🔒</span>
              <input
                type={showPassword ? "text" : "password"}
                value={accessCode}
                onChange={e => setAccessCode(e.target.value)}
                placeholder="Enter access code..."
                disabled={loading}
                style={{
                  width: '100%',
                  background: 'rgba(5, 7, 12, 0.8)',
                  color: T.text,
                  border: `1px solid ${T.border}`,
                  borderRadius: 8,
                  padding: '10px 12px 10px 36px',
                  fontSize: 12,
                  outline: 'none',
                  transition: 'border 0.2s',
                  boxSizing: 'border-box',
                  ...mono,
                }}
                onFocus={e => e.target.style.borderColor = T.accent}
                onBlur={e => e.target.style.borderColor = T.border}
              />
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div style={{
              padding: '8px 12px',
              background: 'rgba(255, 61, 90, 0.08)',
              border: `1px solid rgba(255, 61, 90, 0.25)`,
              borderRadius: 6,
              color: T.red,
              fontSize: 9.5,
              lineHeight: 1.4,
              ...mono,
            }}>
              ⚠ {error}
            </div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={loading}
            style={{
              marginTop: 10,
              padding: '12px 18px',
              background: loading ? 'rgba(123, 108, 255, 0.12)' : T.accent,
              color: '#fff',
              border: 'none',
              borderRadius: 8,
              fontSize: 11,
              fontWeight: 700,
              cursor: loading ? 'not-allowed' : 'pointer',
              letterSpacing: '0.08em',
              transition: 'all 0.2s',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8,
              ...mono,
            }}
          >
            {loading ? (
              <>
                <span style={{
                  width: 10, height: 10, border: '2px solid rgba(255,255,255,0.2)',
                  borderTopColor: '#fff', borderRadius: '50%', display: 'inline-block',
                  animation: 'spin 0.6s linear infinite'
                }} />
                VERIFYING CHALLENGE...
              </>
            ) : "DECRYPT & ENTER TERMINAL"}
          </button>
          
          {/* Target backend URL display (debugging context) */}
          <div style={{
            fontSize: 7.5,
            color: T.textDim,
            textAlign: 'center',
            marginTop: 4,
            ...mono,
            opacity: 0.6,
            letterSpacing: '0.04em',
            wordBreak: 'break-all'
          }}>
            NODE_ADDR: {BASE_URL}
          </div>
        </form>
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(12px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
      `}</style>
    </div>
  );
}
