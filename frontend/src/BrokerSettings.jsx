import React, { useState, useEffect } from 'react';
import { formatError } from './utils/formatError';

const T = {
  bg: '#0B0E14',
  panel: '#151A22',
  panelAlt: '#1A202C',
  border: '#2D3748',
  text: '#E2E8F0',
  textMid: '#A0AEC0',
  accent: '#5E43F3', // Deep purple/blue
  accentHover: '#6c5ce7',
  blue: '#4DA6FF',
  green: '#00E676',
  red: '#FF3B69',
  orange: '#FF9800'
};

const mono = { fontFamily: '"JetBrains Mono", "Roboto Mono", monospace' };

export default function BrokerSettings({ apiFetch }) {
  const [credentials, setCredentials] = useState({
    api_key: '',
    client_code: '',
    pin: '',
    totp_secret: ''
  });
  const [status, setStatus] = useState({ connected: false });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    checkConnectionStatus();
  }, []);

  const checkConnectionStatus = async () => {
    try {
      const res = await apiFetch('/api/angelone/status');
      if (res.ok) {
        const data = await res.json();
        setStatus(data || { connected: false });
        // SECURITY: Backend no longer returns sensitive credentials (api_key, pin, totp_secret).
        // We only pre-fill the client_code (non-sensitive). The user must re-enter
        // credentials on each fresh login for security.
        if (data && data.client_code) {
          setCredentials(prev => ({
            ...prev,
            client_code: data.client_code || prev.client_code
          }));
        }
      } else {
        setStatus({ connected: false });
      }
    } catch (err) {
      console.error('Status check failed:', err);
      setStatus({ connected: false });
    }
  };

  const handleConnect = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const res = await apiFetch('/api/angelone/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(credentials)
      });

      if (res.ok) {
        const data = await res.json();
        if (data && data.status === 'success') {
          setStatus({ connected: true, client_code: data.client_code });
          // Clear credentials from state for security
          setCredentials({
            api_key: '',
            client_code: data.client_code,
            pin: '',
            totp_secret: ''
          });
          return;
        }
      }

      // If we reach here, it failed. Try to parse error detail
      let errMessage = 'Connection failed';
      try {
        const errData = await res.json();
        if (errData) {
          errMessage = formatError(errData.detail || errData.message || errData, 'Connection failed');
        }
      } catch (_) {}
      setError(formatError(errMessage, 'Connection failed'));
    } catch (err) {
      setError(formatError(err, 'Connection failed'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      background: T.panel,
      border: `1px solid ${T.border}`,
      borderRadius: 12,
      padding: 24,
      boxShadow: '0 8px 30px rgba(0,0,0,0.2)'
    }}>
      <h3 style={{ fontSize: 13, fontWeight: 700, letterSpacing: '0.04em', color: '#fff', marginBottom: 16, ...mono }}> ANGELONE BROKER INTEGRATION</h3>
      
      {status.connected ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: T.panelAlt,
            border: `1px solid ${T.border}`,
            padding: '12px 16px',
            borderRadius: 8
          }}>
            <div>
              <div style={{ fontSize: 11, color: T.textMid }}>Broker Connection Status</div>
              <div style={{ fontSize: 14, fontWeight: 700, color: T.green, marginTop: 2 }}>
                CONNECTED
              </div>
            </div>
            <div style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: T.green,
              boxShadow: `0 0 10px ${T.green}`
            }} />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, background: T.panelAlt, padding: 12, borderRadius: 8, border: `1px solid ${T.border}`, fontSize: 11 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: T.textMid }}>Client Code</span>
              <span style={{ color: '#fff', fontWeight: 600, ...mono }}>{status.client_code}</span>
            </div>
          </div>

          <button
            onClick={checkConnectionStatus}
            style={{
              width: '100%',
              padding: '10px 14px',
              background: 'rgba(77, 166, 255, 0.08)',
              border: `1px solid ${T.blue}40`,
              borderRadius: 8,
              color: T.blue,
              fontSize: 12,
              fontWeight: 700,
              cursor: 'pointer',
              ...mono
            }}
          >
            REFRESH STATUS
          </button>
        </div>
      ) : (
        <form onSubmit={handleConnect} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div>
            <label style={{ fontSize: 11, color: T.textMid, display: 'block', marginBottom: 4 }}>API Key</label>
            <input
              type="text"
              value={credentials.api_key}
              onChange={(e) => setCredentials({...credentials, api_key: e.target.value})}
              placeholder="Your AngelOne API Key"
              required
              style={{
                width: '100%', padding: '10px 12px', background: T.panelAlt, border: `1px solid ${T.border}`,
                borderRadius: 6, color: '#fff', outline: 'none', fontSize: 12, ...mono
              }}
            />
          </div>

          <div>
            <label style={{ fontSize: 11, color: T.textMid, display: 'block', marginBottom: 4 }}>Client Code</label>
            <input
              type="text"
              value={credentials.client_code}
              onChange={(e) => setCredentials({...credentials, client_code: e.target.value})}
              placeholder="A12345"
              required
              style={{
                width: '100%', padding: '10px 12px', background: T.panelAlt, border: `1px solid ${T.border}`,
                borderRadius: 6, color: '#fff', outline: 'none', fontSize: 12, ...mono
              }}
            />
          </div>

          <div>
            <label style={{ fontSize: 11, color: T.textMid, display: 'block', marginBottom: 4 }}>Trading PIN (MPIN)</label>
            <input
              type="password"
              value={credentials.pin}
              onChange={(e) => setCredentials({...credentials, pin: e.target.value})}
              placeholder="4-digit PIN"
              maxLength={4}
              required
              style={{
                width: '100%', padding: '10px 12px', background: T.panelAlt, border: `1px solid ${T.border}`,
                borderRadius: 6, color: '#fff', outline: 'none', fontSize: 12, ...mono
              }}
            />
          </div>

          <div>
            <label style={{ fontSize: 11, color: T.textMid, display: 'block', marginBottom: 4 }}>TOTP Secret Key</label>
            <input
              type="text"
              value={credentials.totp_secret}
              onChange={(e) => setCredentials({...credentials, totp_secret: e.target.value})}
              placeholder="BASE32 secret from AngelOne app"
              required
              style={{
                width: '100%', padding: '10px 12px', background: T.panelAlt, border: `1px solid ${T.border}`,
                borderRadius: 6, color: '#fff', outline: 'none', fontSize: 12, ...mono
              }}
            />
            <div style={{ fontSize: 10, color: T.textMid, marginTop: 4 }}>
              Find this in AngelOne app → Settings → API → TOTP Secret
            </div>
          </div>

          {error && <div style={{ fontSize: 12, color: T.red, background: 'rgba(255, 59, 105, 0.1)', padding: 8, borderRadius: 4, ...mono }}>{error}</div>}

          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%',
              padding: '12px 14px',
              background: loading ? T.textMid : T.accent,
              border: 'none',
              borderRadius: 8,
              color: '#fff',
              fontSize: 12,
              fontWeight: 700,
              cursor: loading ? 'not-allowed' : 'pointer',
              marginTop: 8,
              ...mono
            }}
          >
            {loading ? 'CONNECTING...' : 'CONNECT ANGELONE'}
          </button>
        </form>
      )}

      <div style={{ marginTop: 24, padding: 12, background: 'rgba(255, 152, 0, 0.1)', border: `1px solid ${T.orange}40`, borderRadius: 8 }}>
        <h3 style={{ fontSize: 11, fontWeight: 700, color: T.orange, marginBottom: 8, ...mono }}> HOW TO GET CREDENTIALS:</h3>
        <ol style={{ fontSize: 11, color: T.textMid, paddingLeft: 16, margin: 0, lineHeight: 1.5 }}>
          <li>Login to SmartAPI Portal</li>
          <li>Generate API Key from Dashboard</li>
          <li>Enable TOTP and note down the secret key</li>
          <li>Your Client Code is your AngelOne User ID</li>
        </ol>
      </div>
    </div>
  );
}
