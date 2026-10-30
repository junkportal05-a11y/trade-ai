import { describe, it, expect } from 'vitest';
import { describeHttpError, statusFromError } from './apiErrors';

describe('statusFromError', () => {
  it('extracts an HTTP status embedded in the error message', () => {
    expect(statusFromError(new Error('HTTP 503: Service Unavailable'))).toBe(503);
  });

  it('prefers an explicit status property', () => {
    expect(statusFromError({ status: 429, message: 'nope' })).toBe(429);
  });

  it('classifies fetch TypeErrors as network failures', () => {
    expect(statusFromError(new TypeError('Failed to fetch'))).toBe('network');
  });

  it('returns null for unknown errors', () => {
    expect(statusFromError(new Error('boom'))).toBeNull();
    expect(statusFromError(null)).toBeNull();
  });
});

describe('describeHttpError', () => {
  it('distinguishes timeouts (AbortError) from other failures', () => {
    const msg = describeHttpError(new DOMException('aborted', 'AbortError'), 'chart data');
    expect(msg).toMatch(/timed out/i);
    expect(msg).not.toMatch(/offline|server/i);
  });

  it('maps 5xx to a server-error message, not an offline claim', () => {
    expect(describeHttpError(new Error('HTTP 500'))).toMatch(/server hit an error \(500\)/i);
  });

  it('maps 401/403 to an auth message', () => {
    expect(describeHttpError(new Error('HTTP 401'))).toMatch(/not authorized/i);
  });

  it('maps network TypeErrors to a connection message', () => {
    expect(describeHttpError(new TypeError('Failed to fetch'), 'scanner')).toMatch(/reach the server/i);
  });

  it('keeps a plain fallback for undecodable errors', () => {
    expect(describeHttpError(new Error('boom'), 'scanner')).toMatch(/Failed to load scanner/i);
  });

  it('never hardcodes an offline claim for empty-but-OK results', () => {
    expect('HTTP 200').not.toMatch(/offline/i);
  });
});
