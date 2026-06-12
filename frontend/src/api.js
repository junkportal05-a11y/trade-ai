let base = import.meta.env.VITE_API_URL || "";
if (base && !base.startsWith("http")) {
  base = "https://" + base;
}
if (base.endsWith("/")) {
  base = base.slice(0, -1);
}
export const API_BASE_URL = base;

// Authenticated fetch — always sends session cookie and auth token header
export const apiFetch = async (path, options = {}) => {
  const url = path.startsWith("http") ? path : `${API_BASE_URL}${path}`;
  const token = sessionStorage.getItem('apt_token') || localStorage.getItem('apt_token') || '';
  
  const res = await fetch(url, {
    credentials: "include",
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { "X-Session-Token": token, "Authorization": `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });

  if (res.status === 401) {
    localStorage.removeItem('is_logged_in');
    localStorage.removeItem('apex_user');
    localStorage.removeItem('apt_token');
    sessionStorage.removeItem('apt_token');
    if (typeof window !== "undefined") {
      window.location.reload();
    }
  }

  return res;
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
