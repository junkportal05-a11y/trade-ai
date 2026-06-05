import React, { useState } from 'react';

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
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  // Set selected secure credentials
  const VALID_USER = "apex_trader";
  const VALID_PASS = "apex_password";

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');
    
    if (!username.trim() || !password.trim()) {
      setError("Please fill in all security fields.");
      return;
    }

    setLoading(true);

    // Simulate cryptographic challenge verification delay
    setTimeout(() => {
      if (username.trim() === VALID_USER && password === VALID_PASS) {
        onLogin();
      } else {
        setError("AUTHENTICATION FAILED: Invalid credentials.");
        setLoading(false);
      }
    }, 1200);
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
        border: `1px solid ${T.borderHi}`,
        borderRadius: 16,
        padding: '30px 24px',
        boxShadow: '0 20px 40px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.05)',
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
          <span style={{ fontSize: 7.5, color: T.textDim, letterSpacing: '0.15em', ...mono }}>SECURITY GATEWAY v1.0.8</span>
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
          {/* User ID Input */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <label style={{ fontSize: 8.5, color: T.textMid, letterSpacing: '0.08em', ...mono }}>SECURITY USER ID</label>
            <div style={{ position: 'relative' }}>
              <span style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: T.textDim, fontSize: 12 }}>👤</span>
              <input
                type="text"
                value={username}
                onChange={e => setUsername(e.target.value)}
                placeholder="Enter ID..."
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

          {/* Password Input */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label style={{ fontSize: 8.5, color: T.textMid, letterSpacing: '0.08em', ...mono }}>SECURITY KEY (PASSWORD)</label>
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
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="Enter password..."
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
        </form>
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(12px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}
