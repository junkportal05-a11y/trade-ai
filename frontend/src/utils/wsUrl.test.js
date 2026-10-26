import { describe, it, expect } from 'vitest';
import { buildWsUrl } from './wsUrl';

describe('buildWsUrl', () => {
  it('builds a relative URL with encoded query params', () => {
    expect(buildWsUrl('', '/ws/bot', { token: 'a b' })).toBe('/ws/bot?token=a+b');
  });

  it('does not duplicate the /ws prefix when the base already ends with /ws', () => {
    expect(buildWsUrl('ws://localhost:8000/ws', '/ws/bot', { token: 'jwt' }))
      .toBe('ws://localhost:8000/ws/bot?token=jwt');
  });

  it('appends to an origin-only base and skips empty params', () => {
    expect(buildWsUrl('wss://api.example.com/', '/ws/prices', { symbols: 'A,B', token: '' }))
      .toBe('wss://api.example.com/ws/prices?symbols=A%2CB');
  });
});
