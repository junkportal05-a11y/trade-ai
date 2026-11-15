import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { apiFetch, buildApiHeaders, deletePrediction } from './api';

const makeStorage = (initial = {}) => {
  const store = new Map(Object.entries(initial));
  return {
    getItem: (key) => (store.has(key) ? store.get(key) : null),
    setItem: (key, value) => store.set(key, String(value)),
    removeItem: (key) => store.delete(key),
  };
};

describe('buildApiHeaders', () => {
  it('omits JSON Content-Type for FormData uploads but keeps CSRF headers', () => {
    const headers = buildApiHeaders({ method: 'POST', body: new FormData() }, 'csrf-token');

    expect(headers['Content-Type']).toBeUndefined();
    expect(headers['X-CSRF-Token']).toBe('csrf-token');
    expect(headers['X-Requested-With']).toBe('XMLHttpRequest');
  });

  it('sets JSON Content-Type for regular bodies without a CSRF token', () => {
    const headers = buildApiHeaders({ method: 'POST', body: JSON.stringify({ a: 1 }) }, '');

    expect(headers['Content-Type']).toBe('application/json');
    expect(headers['X-CSRF-Token']).toBeUndefined();
  });
});

describe('apiFetch', () => {
  beforeEach(() => {
    // Resolve relative paths deterministically, even when a local .env.local
    // exports a VITE_API_URL (tests assert the path, not the base).
    vi.stubEnv('VITE_API_URL', '');
    vi.stubGlobal('sessionStorage', makeStorage({ apt_csrf: 'csrf-token' }));
    vi.stubGlobal('localStorage', makeStorage());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it('keeps JSON Content-Type for JSON bodies and sends the CSRF header', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200 });
    vi.stubGlobal('fetch', fetchMock);

    await apiFetch('/api/chat', { method: 'POST', body: JSON.stringify({ message: 'hi' }) });

    const [, options] = fetchMock.mock.calls[0];
    expect(options.headers['Content-Type']).toBe('application/json');
    expect(options.headers['X-CSRF-Token']).toBe('csrf-token');
    expect(options.headers.Authorization).toBeUndefined();
  });

  it('sends chart uploads with credentials and CSRF header, letting the browser set multipart boundary', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200 });
    vi.stubGlobal('fetch', fetchMock);
    const body = new FormData();

    await apiFetch('/api/chat/chart/upload', { method: 'POST', body });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/chat/chart/upload');
    expect(options.credentials).toBe('include');
    expect(options.body).toBe(body);
    expect(options.headers['Content-Type']).toBeUndefined();
    expect(options.headers['X-CSRF-Token']).toBe('csrf-token');
  });
});

describe('deletePrediction', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_API_URL', '');
    vi.stubGlobal('sessionStorage', makeStorage({ apt_csrf: 'csrf-token' }));
    vi.stubGlobal('localStorage', makeStorage());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it('sends DELETE /api/predictions/{id} with the CSRF header', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200 });
    vi.stubGlobal('fetch', fetchMock);

    await deletePrediction(42);

    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/predictions/42');
    expect(options.method).toBe('DELETE');
    expect(options.credentials).toBe('include');
    expect(options.headers['X-CSRF-Token']).toBe('csrf-token');
    expect(options.headers.Authorization).toBeUndefined();
  });
});
