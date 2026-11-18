import React, { useState, useEffect, useRef } from 'react';
import { T } from '../theme';
import { Lock, AlertCircle, Eye, EyeOff, Loader2 } from 'lucide-react';

export default function CodeEntryScreen({ onVerified }) {
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showCode, setShowCode] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!code.trim()) {
      setError('Enter the access code');
      return;
    }
    setError('');
    setLoading(true);
    try {
      const base = window.__API_BASE_URL__ || '';
      const res = await fetch(`${base}/api/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ username: 'code', password: code.trim() }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || 'Invalid code');
      }
      const data = await res.json();
      if (data.csrf_token) {
        sessionStorage.setItem('apt_csrf', data.csrf_token);
        localStorage.setItem('apt_csrf', data.csrf_token);
        // Also store the auth token for WebSocket connection
        if (data.token) {
          sessionStorage.setItem('apt_token', data.token);
          localStorage.setItem('apt_token', data.token);
        }
        onVerified(data);
      } else {
        throw new Error('No CSRF token received');
      }
    } catch (err) {
      setError(err.message || 'Authentication failed');
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        background: T.bg,
        color: T.text,
        fontFamily: "'Inter', system-ui, sans-serif",
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: 360,
          background: T.panel,
          border: `1px solid ${T.borderHi}`,
          borderRadius: 12,
          padding: 32,
          boxShadow: '0 8px 32px rgba(0,0,0,0.6)',
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <Lock size={40} color={T.accentAlt} style={{ marginBottom: 12 }} />
          <h1 style={{ margin: 0, fontSize: 20, fontWeight: 600, letterSpacing: '0.02em' }}>
            ApexTrade Workstation
          </h1>
          <p style={{ margin: '8px 0 0', fontSize: 13, color: '#8290ad' }}>
            Single-user access. Enter the access code to continue.
          </p>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div style={{ position: 'relative' }}>
            <input
              ref={inputRef}
              type={showCode ? 'text' : 'password'}
              value={code}
              onChange={(e) => setCode(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSubmit(e)}
              placeholder="Access code"
              disabled={loading}
              autoComplete="off"
              spellCheck={false}
              style={{
                width: '100%',
                padding: '14px 48px 14px 14px',
                background: T.bg,
                border: `1px solid ${T.border}`,
                borderRadius: 8,
                color: T.text,
                fontSize: 15,
                fontFamily: "'IBM Plex Mono', monospace",
                letterSpacing: '0.08em',
                outline: 'none',
                boxSizing: 'border-box',
                transition: 'border-color 0.15s',
              }}
            />
            <button
              type="button"
              onClick={() => setShowCode(!showCode)}
              style={{
                position: 'absolute',
                right: 12,
                top: '50%',
                transform: 'translateY(-50%)',
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                padding: 4,
                color: T.textDim,
              }}
            >
              {showCode ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>

          {error && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '10px 12px',
                background: T.redDim,
                border: `1px solid ${T.redGlow}`,
                borderRadius: 8,
                color: T.red,
                fontSize: 12,
                fontWeight: 500,
              }}
            >
              <AlertCircle size={14} /> {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !code.trim()}
            style={{
              padding: '14px',
              background: loading ? T.borderHi : T.accentAlt,
              color: loading ? T.textDim : T.bg,
              border: 'none',
              borderRadius: 8,
              fontSize: 14,
              fontWeight: 600,
              fontFamily: "'Inter', sans-serif",
              letterSpacing: '0.04em',
              cursor: loading ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8,
              transition: 'background 0.15s',
            }}
          >
            {loading ? (
              <>
                <Loader2 size={16} style={{ animation: 'spin 0.8s linear infinite' }} />
                Verifying...
              </>
            ) : (
              'Enter Terminal'
            )}
          </button>
        </form>

        <p style={{ margin: '20px 0 0', fontSize: 11, color: T.textMuted, textAlign: 'center', lineHeight: 1.5 }}>
          No signup. No recovery. No roles. This is a personal quant workstation.
        </p>
      </div>

      <style jsx>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        input:focus { border-color: ${T.accentAlt} !important; }
        button:not(:disabled):hover { background: ${T.accentAlt}; }
      `}</style>
    </div>
  );
}
