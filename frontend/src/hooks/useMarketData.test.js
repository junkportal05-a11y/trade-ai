import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import { isNSEMarketOpen, tickToQuote } from './useMarketData';

describe('isNSEMarketOpen', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should return false on Sunday', () => {
    // 2023-10-15 is a Sunday
    const date = new Date('2023-10-15T12:00:00Z');
    vi.setSystemTime(date);
    expect(isNSEMarketOpen()).toBe(false);
  });

  it('should return false on Saturday', () => {
    // 2023-10-14 is a Saturday
    const date = new Date('2023-10-14T12:00:00Z');
    vi.setSystemTime(date);
    expect(isNSEMarketOpen()).toBe(false);
  });

  it('should return false before market opens on a weekday (e.g. Monday 9:00 AM IST)', () => {
    // Monday 9:00 AM IST = Monday 3:30 AM UTC
    // 2023-10-16 is a Monday
    const date = new Date('2023-10-16T03:30:00Z');
    vi.setSystemTime(date);
    expect(isNSEMarketOpen()).toBe(false);
  });

  it('should return true exactly at market open on a weekday (e.g. Monday 9:15 AM IST)', () => {
    // Monday 9:15 AM IST = Monday 3:45 AM UTC
    const date = new Date('2023-10-16T03:45:00Z');
    vi.setSystemTime(date);
    expect(isNSEMarketOpen()).toBe(true);
  });

  it('should return true during market hours on a weekday (e.g. Monday 12:00 PM IST)', () => {
    // Monday 12:00 PM IST = Monday 6:30 AM UTC
    const date = new Date('2023-10-16T06:30:00Z');
    vi.setSystemTime(date);
    expect(isNSEMarketOpen()).toBe(true);
  });

  it('should return true exactly at market close on a weekday (e.g. Monday 3:30 PM IST)', () => {
    // Monday 3:30 PM IST = Monday 10:00 AM UTC
    const date = new Date('2023-10-16T10:00:00Z');
    vi.setSystemTime(date);
    expect(isNSEMarketOpen()).toBe(true);
  });

  it('should return false after market closes on a weekday (e.g. Monday 4:00 PM IST)', () => {
    // Monday 4:00 PM IST = Monday 10:30 AM UTC
    const date = new Date('2023-10-16T10:30:00Z');
    vi.setSystemTime(date);
    expect(isNSEMarketOpen()).toBe(false);
  });
});

describe('tickToQuote', () => {
  it('labels every /api/prices and /ws/prices tick as simulated', () => {
    const quote = tickToQuote({ symbol: 'SBIN.NS', price: 101, prev_close: 100, timestamp: 't' }, undefined);

    expect(quote.source).toBe('simulated');
    expect(quote.change).toBe(1);
    expect(quote.changePct).toBe(1);
  });

  it('falls back to the previous quote close, then the tick price', () => {
    expect(tickToQuote({ price: 50 }, { prevClose: 40 }).changePct).toBe(25);
    expect(tickToQuote({ price: 50 }, undefined).change).toBe(0);
  });
});
