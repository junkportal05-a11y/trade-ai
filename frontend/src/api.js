let base = import.meta.env.VITE_API_URL || "";
if (base && !base.startsWith("http")) {
  base = "https://" + base;
}
if (base.endsWith("/")) {
  base = base.slice(0, -1);
}
export const API_BASE_URL = base;

// Authenticated fetch — always sends session cookie and auth token header
export const apiFetch = (path, options = {}) => {
  const url = path.startsWith("http") ? path : `${API_BASE_URL}${path}`;
  const token = sessionStorage.getItem('apt_token') || localStorage.getItem('apt_token') || '';
  
  return fetch(url, {
    credentials: "include",
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { "X-Session-Token": token, "Authorization": `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });
};
