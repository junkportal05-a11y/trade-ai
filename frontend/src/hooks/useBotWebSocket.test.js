import { describe, it, expect } from 'vitest';
import { buildBotWsUrl, getReconnectDelay, shouldReconnect } from './useBotWebSocket';

describe('useBotWebSocket helpers', () => {
  it('relies on the session cookie instead of a token query parameter', () => {
    expect(buildBotWsUrl('')).toBe('/ws/bot');
    expect(buildBotWsUrl('wss://api.example.com'))
      .toBe('wss://api.example.com/ws/bot');
  });

  it('does not reconnect after auth close codes', () => {
    expect(shouldReconnect(4001)).toBe(false);
    expect(shouldReconnect(1008)).toBe(false);
    expect(shouldReconnect(1006)).toBe(true);
  });

  it('backs off exponentially up to 30 seconds', () => {
    expect(getReconnectDelay(0)).toBe(3000);
    expect(getReconnectDelay(1)).toBe(6000);
    expect(getReconnectDelay(2)).toBe(12000);
    expect(getReconnectDelay(3)).toBe(24000);
    expect(getReconnectDelay(4)).toBe(30000);
    expect(getReconnectDelay(20)).toBe(30000);
  });
});
