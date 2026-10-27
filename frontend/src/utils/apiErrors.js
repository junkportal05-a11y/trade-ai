// Status-distinguished messages for failed API calls, so UI banners never
// claim the backend is offline when the real problem is a timeout, a server
// error, an expired session, or a request that legitimately returned nothing.
export function statusFromError(err) {
  if (!err) return null;
  if (typeof err.status === 'number') return err.status;
  if (typeof err.message === 'string') {
    const m = err.message.match(/HTTP (\d{3})/);
    if (m) return Number(m[1]);
  }
  if (err.name === 'TypeError') return 'network';
  return null;
}

export function describeHttpError(err, context = 'market data') {
  if (err && (err.name === 'AbortError' || statusFromError(err) === 408)) {
    return `${context} request timed out. Tap RETRY to try again.`;
  }
  const status = statusFromError(err);
  if (status === 400 || status === 401 || status === 403) {
    return `Your session is not authorized for ${context}. Sign in again, then tap RETRY.`;
  }
  if (status === 404) {
    return `No ${context} found for this request. Tap RETRY in case data arrived late.`;
  }
  if (status === 429) {
    return `Too many ${context} requests in a row. Wait a moment, then tap RETRY.`;
  }
  if (typeof status === 'number' && status >= 500) {
    return `The server hit an error (${status}) while loading ${context}. Tap RETRY to try again.`;
  }
  if (status === 'network') {
    return `Could not reach the server for ${context}. Check connection, then tap RETRY.`;
  }
  return `Failed to load ${context}. Tap RETRY to try again.`;
}
