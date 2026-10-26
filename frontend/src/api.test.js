import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

describe('apiFetch', () => {
  let apiFetch;

  beforeEach(async () => {
    vi.stubGlobal('sessionStorage', { getItem: () => 'test-token', removeItem: vi.fn() });
    vi.stubGlobal('localStorage', { getItem: () => null, removeItem: vi.fn() });
    vi.stubGlobal('window', { location: { port: '' }, dispatchEvent: vi.fn() });
    vi.stubGlobal('fetch', vi.fn(async () => ({ status: 200 })));
    ({ apiFetch } = await import('./api'));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('omits JSON Content-Type for FormData uploads and still sends auth headers', async () => {
    const formData = new FormData();
    formData.append('file', new Blob(['x'], { type: 'image/png' }), 'chart.png');

    await apiFetch('/api/chat/chart/upload', { method: 'POST', body: formData });

    const [, options] = fetch.mock.calls[0];
    expect(options.headers['Content-Type']).toBeUndefined();
    expect(options.headers['X-Session-Token']).toBe('test-token');
    expect(options.headers['Authorization']).toBe('Bearer test-token');
    expect(options.headers['X-Requested-With']).toBe('XMLHttpRequest');
    expect(options.credentials).toBe('include');
  });

  it('keeps JSON Content-Type for JSON bodies', async () => {
    await apiFetch('/api/chat', { method: 'POST', body: JSON.stringify({ message: 'hi' }) });

    const [, options] = fetch.mock.calls[0];
    expect(options.headers['Content-Type']).toBe('application/json');
  });
});
