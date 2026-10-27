import { describe, it, expect } from 'vitest';
import { BRIEF_TIMEOUT_MS, briefErrorMessage } from './briefing';

describe('BRIEF_TIMEOUT_MS', () => {
  it('caps briefing waits at 18 seconds', () => {
    expect(BRIEF_TIMEOUT_MS).toBe(18000);
  });
});

describe('briefErrorMessage', () => {
  it('labels a request abort as a timeout', () => {
    const err = new Error('The operation was aborted');
    err.name = 'AbortError';
    const msg = briefErrorMessage(err);
    expect(msg).toMatch(/timed out/i);
    expect(msg).toMatch(/retry/i);
  });

  it('labels HTTP failures as server errors', () => {
    const msg = briefErrorMessage(new Error('HTTP 503'));
    expect(msg).toMatch(/server error/i);
    expect(msg).toMatch(/retry/i);
  });

  it('falls back to connection language for network errors', () => {
    expect(briefErrorMessage(new Error('Failed to fetch'))).toMatch(/connection/i);
    expect(briefErrorMessage(null)).toMatch(/connection/i);
  });
});
