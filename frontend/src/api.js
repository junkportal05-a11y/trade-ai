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
  (API_BASE_URL ? API_BASE_URL.replace(/^https:/i, 'wss:').replace(/^http:/i, 'ws:') : (isDev ? 'ws://localhost:8000' : ''));

// Authenticated fetch — always sends session cookie and auth token header
export const apiFetch = async (path, options = {}) => {
  const currentBase = getApiBaseUrl();
  const url = path.startsWith("http") ? path : `${currentBase}${path}`;
  const token = sessionStorage.getItem('apt_token') || localStorage.getItem('apt_token') || '';

  const isMutating = ["POST", "PUT", "DELETE", "PATCH"].includes((options.method || "GET").toUpperCase());
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;

  const res = await fetch(url, {
    credentials: "include",
    ...options,
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(isMutating ? { "X-Requested-With": "XMLHttpRequest" } : {}),
      ...(token ? { "X-Session-Token": token, "Authorization": `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });

  if (res.status === 401) {
    // Token expired or invalid — clear stored tokens
    sessionStorage.removeItem('apt_token');
    localStorage.removeItem('apt_token');
    // Dispatch event for UI to show code entry screen
    window.dispatchEvent(new CustomEvent('apex:auth-required'));
  }

  return res;
};

// Verify current token with backend
export const verifyToken = async () => {
  const currentBase = getApiBaseUrl();
  const token = sessionStorage.getItem('apt_token') || localStorage.getItem('apt_token') || '';
  if (!token) return false;

  try {
    const res = await fetch(`${currentBase}/api/auth/verify`, {
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'X-Session-Token': token, 'Authorization': `Bearer ${token}` } : {}),
      },
    });
    if (res.ok) return true;
  } catch {
    return false;
  }
  return false;
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
