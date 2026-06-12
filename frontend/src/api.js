let base = import.meta.env.VITE_API_URL || "";
if (base && !base.startsWith("http")) {
  base = "https://" + base;
}
if (base.endsWith("/")) {
  base = base.slice(0, -1);
}
export const API_BASE_URL = base;

// Authenticated fetch — always sends session cookie
export const apiFetch = (path, options = {}) => {
  const url = path.startsWith("http") ? path : `${API_BASE_URL}${path}`;
  return fetch(url, {
    credentials: "include",
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
};
