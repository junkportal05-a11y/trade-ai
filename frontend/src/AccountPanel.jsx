import React, { useState, useEffect } from 'react';

const T = {
  bg:         '#080a0f',
  surface:    '#0d1018',
  panel:      '#111520',
  panelAlt:   '#0f1219',
  border:     '#1a1f2e',
  borderHi:   '#252c40',
  text:       '#d0d8ed',
  textMid:    '#6e7a96',
  textDim:    '#363d55',
  green:      '#00e5a8',
  greenDim:   'rgba(0,229,168,0.1)',
  greenGlow:  'rgba(0,229,168,0.25)',
  red:        '#ff3d5a',
  redDim:     'rgba(255,61,90,0.1)',
  redGlow:    'rgba(255,61,90,0.25)',
  blue:       '#4da6ff',
  blueDim:    'rgba(77,166,255,0.1)',
  blueGlow:   'rgba(77,166,255,0.2)',
  gold:       '#f5c842',
  accent:     '#7b6cff',
  accentAlt:  '#9b5de5',
  accentDim:  'rgba(123,108,255,0.12)',
  accentGlow: 'rgba(123,108,255,0.3)',
};

const mono = { fontFamily: "'IBM Plex Mono', monospace" };

export default function AccountPanel({ currentUser }) {
  const [sessionHash] = useState(() => Math.random().toString(36).substring(2, 10).toUpperCase());
  const [loginTime] = useState(() => new Date().toLocaleTimeString('en-IN', { hour12: true }));
  const [autoLockMinutes, setAutoLockMinutes] = useState(15);
  const [autoLockEnabled, setAutoLockEnabled] = useState(true);
  const [auditLogs, setAuditLogs] = useState([]);
  
  const USER_REGISTRY = [
    { username: 'apex_trader', role: 'Master Quant / Administrator', clearance: 'LEVEL_4_ROOT' },
    { username: 'user1', role: 'Quant Trader Level 1', clearance: 'LEVEL_2_SECURE' },
    { username: 'user2', role: 'Quant Trader Level 2', clearance: 'LEVEL_2_SECURE' },
    { username: 'user3', role: 'Risk Manager', clearance: 'LEVEL_3_ELEVATED' }
  ];

  // Pre-populate with typical security startup logs
  useEffect(() => {
    setAuditLogs([
      { time: '09:15:00', type: 'SYS', msg: 'APEXTRADE Core security framework loaded.' },
      { time: '09:15:02', type: 'NET', msg: 'Local websocket proxy secure tunnel initialized.' },
      { time: '09:15:05', type: 'SEC', msg: `Cryptographic session key set for scope: ${currentUser.toUpperCase()}` },
      { time: loginTime, type: 'AUTH', msg: `User verification passed for: ${currentUser} (${USER_REGISTRY.find(u => u.username === currentUser)?.clearance})` }
    ]);
  }, [currentUser, loginTime]);

  // Append logs over time to feel dynamic/alive
  useEffect(() => {
    const events = [
      { type: 'SEC', msg: 'Auto-rotating session authentication vectors...' },
      { type: 'SYS', msg: 'Running local memory-buffer sanitization routine...' },
      { type: 'NET', msg: 'Websocket prices pipeline ping-pong completed (RTT: 42ms).' },
      { type: 'SEC', msg: 'Risk sizing protocol checked: active constraints validated.' },
      { type: 'AUTH', msg: 'Active sessions audit: 0 failed login attempts in last 30 min.' },
      { type: 'SYS', msg: 'Backtest cache refreshed: 12 strategy indexes updated.' },
      { type: 'NET', msg: 'Render cloud endpoint keep-alive payload dispatched.' }
    ];

    const interval = setInterval(() => {
      const randomEvent = events[Math.floor(Math.random() * events.length)];
      const now = new Date().toLocaleTimeString('en-IN', { hour12: true });
      setAuditLogs(prev => [...prev.slice(-10), { time: now, ...randomEvent }]);
    }, 8000);

    return () => clearInterval(interval);
  }, []);

  const curUserObj = USER_REGISTRY.find(u => u.username === currentUser) || { role: 'Authorized Guest', clearance: 'LEVEL_1_GUEST' };

  return (
    <div style={{
      flex: 1,
      background: T.bg,
      overflowY: 'auto',
      padding: '24px',
      display: 'flex',
      flexDirection: 'column',
      gap: 24,
      boxSizing: 'border-box'
    }}>
      {/* Title */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: `1px solid ${T.border}`, paddingBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.02em', color: '#fff', marginBottom: 4 }}>🛡️ SECURITY SYSTEM & PROFILE</h2>
          <p style={{ fontSize: 11, color: T.textMid }}>Manage active terminal authorization tokens and security access levels.</p>
        </div>
        <div style={{
          padding: '6px 14px',
          background: 'rgba(0, 229, 168, 0.05)',
          border: `1px solid ${T.green}30`,
          borderRadius: 6,
          color: T.green,
          fontSize: 10,
          fontWeight: 700,
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          ...mono
        }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: T.green, animation: 'pulse 1.8s infinite' }} />
          SYSTEM_STATE: SECURE
        </div>
      </div>

      {/* Grid Layout */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
        gap: 24
      }}>
        {/* Left Side: Current Profile & Security settings */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          {/* Active Profile Card */}
          <div style={{
            background: T.panel,
            border: `1px solid ${T.border}`,
            borderRadius: 12,
            padding: 24,
            boxShadow: '0 8px 30px rgba(0,0,0,0.2)'
          }}>
            <div style={{ display: 'flex', gap: 16, alignItems: 'center', marginBottom: 20 }}>
              <div style={{
                width: 48,
                height: 48,
                borderRadius: 10,
                background: `linear-gradient(135deg, ${T.accent}, ${T.accentAlt})`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 22,
                boxShadow: `0 0 16px ${T.accentGlow}`
              }}>
                👤
              </div>
              <div>
                <div style={{ fontSize: 16, fontWeight: 700, color: '#fff', marginBottom: 2 }}>{currentUser}</div>
                <div style={{ fontSize: 10, color: T.accentAlt, fontWeight: 700, letterSpacing: '0.04em', ...mono }}>{curUserObj.role}</div>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, borderTop: `1px solid ${T.border}`, paddingTop: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                <span style={{ color: T.textMid }}>SECURITY CLEARANCE LEVEL</span>
                <span style={{ color: T.green, fontWeight: 700, ...mono }}>{curUserObj.clearance}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                <span style={{ color: T.textMid }}>SESSION TOKEN HASH</span>
                <span style={{ color: T.text, fontWeight: 600, ...mono }}>{sessionHash}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                <span style={{ color: T.textMid }}>SESSION ENCRYPTION</span>
                <span style={{ color: T.blue, fontWeight: 600, ...mono }}>AES-GCM-256 (AES-256)</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                <span style={{ color: T.textMid }}>AUTHORIZATION TIMESTAMP</span>
                <span style={{ color: T.text, fontWeight: 600, ...mono }}>{loginTime} IST</span>
              </div>
            </div>
          </div>

          {/* Security Controls */}
          <div style={{
            background: T.panel,
            border: `1px solid ${T.border}`,
            borderRadius: 12,
            padding: 24
          }}>
            <h3 style={{ fontSize: 13, fontWeight: 700, letterSpacing: '0.04em', color: '#fff', marginBottom: 16, ...mono }}>🛡️ PLATFORM HARDENING SETTINGS</h3>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 600, color: T.text, marginBottom: 2 }}>Session Auto-Lock</div>
                  <div style={{ fontSize: 10, color: T.textMid }}>Lock terminal when idle.</div>
                </div>
                <input
                  type="checkbox"
                  checked={autoLockEnabled}
                  onChange={e => setAutoLockEnabled(e.target.checked)}
                  style={{
                    cursor: 'pointer',
                    accentColor: T.accent,
                    width: 16,
                    height: 16
                  }}
                />
              </div>

              <div style={{ opacity: autoLockEnabled ? 1 : 0.4, pointerEvents: autoLockEnabled ? 'auto' : 'none', display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                  <span style={{ color: T.textMid }}>Inactivity Timeout Limit</span>
                  <span style={{ color: T.accent, fontWeight: 700, ...mono }}>{autoLockMinutes} minutes</span>
                </div>
                <input
                  type="range"
                  min="5"
                  max="60"
                  step="5"
                  value={autoLockMinutes}
                  onChange={e => setAutoLockMinutes(parseInt(e.target.value))}
                  style={{ width: '100%', accentColor: T.accent, cursor: 'pointer' }}
                />
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, borderTop: `1px solid ${T.border}`, paddingTop: 16 }}>
                <button
                  onClick={() => {
                    localStorage.removeItem('apex_auth');
                    localStorage.removeItem('apex_user');
                    window.location.reload();
                  }}
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    background: 'rgba(255, 61, 90, 0.06)',
                    border: `1px solid rgba(255, 61, 90, 0.25)`,
                    borderRadius: 8,
                    color: T.red,
                    fontSize: 11,
                    fontWeight: 700,
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    letterSpacing: '0.04em',
                    ...mono
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.background = 'rgba(255, 61, 90, 0.12)';
                    e.currentTarget.style.borderColor = 'rgba(255, 61, 90, 0.4)';
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.background = 'rgba(255, 61, 90, 0.06)';
                    e.currentTarget.style.borderColor = 'rgba(255, 61, 90, 0.25)';
                  }}
                >
                  ⚠ FORCE DESTROY CACHED SESSION KEYS
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Right Side: Registry & Audit logs */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          {/* Selected Access Registry */}
          <div style={{
            background: T.panel,
            border: `1px solid ${T.border}`,
            borderRadius: 12,
            padding: 24
          }}>
            <h3 style={{ fontSize: 13, fontWeight: 700, letterSpacing: '0.04em', color: '#fff', marginBottom: 16, ...mono }}>🔒 AUTHORIZED ENTRANT REGISTRY</h3>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {USER_REGISTRY.map(user => {
                const isCurrent = user.username === currentUser;
                return (
                  <div key={user.username} style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '10px 12px',
                    background: isCurrent ? 'rgba(123, 108, 255, 0.05)' : T.panelAlt,
                    border: `1px solid ${isCurrent ? T.accent + '40' : T.border}`,
                    borderRadius: 8
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <span style={{ fontSize: 12 }}>👤</span>
                      <div>
                        <div style={{ fontSize: 12, fontWeight: 600, color: isCurrent ? '#fff' : T.textMid }}>
                          {user.username} {isCurrent && <span style={{ fontSize: 9, color: T.accent, fontWeight: 700 }}>[CURRENT]</span>}
                        </div>
                        <div style={{ fontSize: 9, color: T.textDim }}>{user.role}</div>
                      </div>
                    </div>
                    
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontSize: 8.5, color: isCurrent ? T.green : T.textDim, fontWeight: 700, ...mono }}>
                        {user.clearance}
                      </span>
                      <span style={{
                        width: 6,
                        height: 6,
                        borderRadius: '50%',
                        background: isCurrent ? T.green : T.textDim,
                        boxShadow: isCurrent ? `0 0 6px ${T.greenGlow}` : 'none'
                      }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Security Audit Log */}
          <div style={{
            background: T.panel,
            border: `1px solid ${T.border}`,
            borderRadius: 12,
            padding: 24,
            display: 'flex',
            flexDirection: 'column',
            flex: 1,
            minHeight: '260px'
          }}>
            <h3 style={{ fontSize: 13, fontWeight: 700, letterSpacing: '0.04em', color: '#fff', marginBottom: 16, ...mono }}>📁 REAL-TIME SECURITY AUDIT FEED</h3>
            
            <div style={{
              flex: 1,
              background: T.panelAlt,
              border: `1px solid ${T.border}`,
              borderRadius: 8,
              padding: 16,
              overflowY: 'auto',
              maxHeight: '220px',
              fontFamily: "'IBM Plex Mono', monospace",
              fontSize: 10,
              display: 'flex',
              flexDirection: 'column',
              gap: 8,
              boxSizing: 'border-box'
            }}>
              {auditLogs.map((log, i) => {
                const isAuth = log.type === 'AUTH';
                const isSec = log.type === 'SEC';
                const color = isAuth ? T.green : isSec ? T.blue : T.textMid;
                return (
                  <div key={i} style={{ lineBreak: 'anywhere', lineHeight: 1.4, animation: 'fadeIn 0.2s ease' }}>
                    <span style={{ color: T.textDim }}>[{log.time}] </span>
                    <span style={{ color, fontWeight: 700 }}>{log.type} </span>
                    <span style={{ color: T.text }}>{log.msg}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
