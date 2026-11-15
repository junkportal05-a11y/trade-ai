export const getApiBaseUrl = () => {
  if (typeof window !== "undefined") {
    const custom = localStorage.getItem('apex_api_url');
    if (custom) return custom.endsWith('/') ? custom.slice(0, -1) : custom;
  }
  let base = import.meta.env.VITE_API_URL || "";
  if (base && !base.startsWith("http")) {
    base = "https://" + base;
  }
  if (base.endsWith("/")) {
    base = base.slice(0, -1);
  }
  return base;
};

export const setApiBaseUrl = (url) => {
  if (typeof window !== "undefined") {
    if (!url) {
      localStorage.removeItem('apex_api_url');
    } else {
      let clean = url.trim();
      if (!clean.startsWith("http")) clean = "https://" + clean;
      if (clean.endsWith("/")) clean = clean.slice(0, -1);
      localStorage.setItem('apex_api_url', clean);
    }
  }
};

export const API_BASE_URL = getApiBaseUrl();

const isDev = typeof window !== "undefined" && window.location.port === "5173";
export const WS_BASE_URL = import.meta.env.VITE_WS_URL || 
  (API_BASE_URL ? API_BASE_URL.replace(/^https:/i, 'wss:').replace(/^http:/i, 'ws:') : (isDev ? 'ws://localhost:8000/ws' : ''));

// Build headers for apiFetch. Multipart bodies must not get a JSON
// Content-Type or the browser boundary is lost. Mutating requests carry the
// double-submit CSRF token alongside the session cookie.
export const buildApiHeaders = (options = {}, csrfToken = '') => {
  const bodyIsFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;
  const isMutating = ["POST", "PUT", "DELETE", "PATCH"].includes((options.method || "GET").toUpperCase());

  return {
    ...(bodyIsFormData ? {} : { "Content-Type": "application/json" }),
    ...(isMutating ? { "X-Requested-With": "XMLHttpRequest" } : {}),
    ...(isMutating && csrfToken ? { "X-CSRF-Token": csrfToken } : {}),
    ...(options.headers || {}),
  };
};

const getCsrfToken = () =>
  sessionStorage.getItem('apt_csrf') || localStorage.getItem('apt_csrf') || '';

const clearAuth = () => {
  sessionStorage.removeItem('apt_token');
  sessionStorage.removeItem('apt_csrf');
  localStorage.removeItem('apt_token');
  localStorage.removeItem('apt_csrf');
};

// Authenticated fetch — always sends the session cookie and CSRF token header
// Returns a Response-like object with fallback data on network/API failure
export const apiFetch = async (path, options = {}) => {
  const currentBase = getApiBaseUrl();
  const url = path.startsWith("http") ? path : `${currentBase}${path}`;

  try {
    const res = await fetch(url, {
      credentials: "include",
      ...options,
      headers: buildApiHeaders(options, getCsrfToken()),
    });

    if (res.status === 401) {
      clearAuth();
      window.dispatchEvent(new CustomEvent('apex:auth-required'));
    }

    return res;
  } catch {
    // Network error — return a mock Response with fallback data
    const fallback = buildFallback(path, options);
    return new Response(JSON.stringify(fallback), {
      status: 503,
      statusText: 'Service Unavailable',
      headers: { 'Content-Type': 'application/json' },
    });
  }
};

// Fallback data structures for each API endpoint — ensures UI never crashes on network failure
function buildFallback(path, options) {
  const isPost = (options.method || 'GET').toUpperCase() === 'POST';

  if (path === '/api/strategies' || path === '/api/strategies/') {
    return { strategies: [], active: [] };
  }
  if (path === '/api/predictions' || path === '/api/predictions/') {
    return { predictions: [], stats: { total: 0, resolved: 0, winRate: 0 } };
  }
  if (path === '/api/predictions/stats') {
    return { total: 0, resolved: 0, winRate: 0 };
  }
  if (path.startsWith('/api/predictions/') && path.includes('/resolve')) {
    return { success: true, resolved: true };
  }
  if (path === '/api/allocate') {
    return { allocations: {}, confidence: 0, signal: 'HOLD', reasoning: 'Network unavailable' };
  }
  if (path === '/api/signals' || path === '/api/signals/') {
    return { signals: [], timestamp: Date.now() };
  }
  if (path === '/api/scan') {
    return { results: [], scanTime: Date.now() };
  }
  if (path === '/api/market_brief') {
    return { brief: 'Market data unavailable', timestamp: Date.now() };
  }
  if (path === '/api/history') {
    return { candles: [], symbol: '', interval: '', range: '' };
  }
  if (path === '/api/chat') {
    return { reply: 'AI service unavailable. Please try again later.', confidence: 0 };
  }
  if (path === '/api/chat/chart') {
    return { analysis: { trend: 'unknown', patterns: [], confidence: 0 } };
  }
  if (path === '/api/bot/start' || path === '/api/bot/pause' || path === '/api/bot/stop') {
    return { success: false, error: 'Network error' };
  }
  if (path === '/api/journal' || path === '/api/journal/') {
    return { entries: [], stats: { totalTrades: 0, winRate: 0, pnl: 0 } };
  }
  if (path === '/api/backtest/run' || path === '/api/backtest/tournament' || path === '/api/backtest/tournament/leaderboard') {
    return { results: [], leaderboard: [] };
  }
  if (path === '/api/angelone/status' || path === '/api/angelone/login') {
    return { status: 'disconnected', error: 'Network unavailable' };
  }
  if (path === '/api/data/confidence') {
    return { confidence: 0.5, lastUpdate: Date.now() };
  }
  if (path === '/api/admin/run-simulation' || path === '/api/admin/simulation-status') {
    return { success: false, error: 'Network error' };
  }
  if (path === '/api/auth/verify') {
    return { valid: false };
  }
  if (path === '/api/prices') {
    return { prices: {} };
  }

  // Generic fallback for unknown endpoints
  return isPost ? { success: false, error: 'Network unavailable' } : { data: null, error: 'Network unavailable' };
}

// Verify the session cookie and refresh the CSRF token when needed.
export const verifyToken = async () => {
  const currentBase = getApiBaseUrl();

  try {
    const res = await fetch(`${currentBase}/api/auth/verify`, {
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) return false;
    const data = await res.json().catch(() => ({}));
    if (data.csrf_token) {
      sessionStorage.setItem('apt_csrf', data.csrf_token);
      localStorage.setItem('apt_csrf', data.csrf_token);
    }
    return true;
  } catch {
    return false;
  }
};

// Admin Simulation Endpoints
export const runHistoricalSimulation = (start_date, end_date, adminKey) => apiFetch('/api/admin/run-simulation', {
  method: 'POST',
  headers: { 'x-admin-key': adminKey },
  body: JSON.stringify({ start_date, end_date })
});

export const getSimulationStatus = (adminKey) => apiFetch('/api/admin/simulation-status', {
  headers: { 'x-admin-key': adminKey }
});

// Predictions
export const deletePrediction = (predictionId) => apiFetch(`/api/predictions/${encodeURIComponent(predictionId)}`, {
  method: 'DELETE'
});
