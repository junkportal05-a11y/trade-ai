// Join a WebSocket base URL with a path and query params without duplicating
// the /ws prefix (the dev fallback base already ends in /ws).
export function buildWsUrl(baseUrl, path, params = {}) {
  const base = String(baseUrl || '').replace(/\/+$/, '');
  let wsPath = path.startsWith('/') ? path : `/${path}`;

  if (base.endsWith('/ws') && wsPath.startsWith('/ws/')) {
    wsPath = wsPath.slice(3);
  }

  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      query.set(key, String(value));
    }
  });

  const suffix = query.toString();
  return `${base}${wsPath}${suffix ? `?${suffix}` : ''}`;
}
