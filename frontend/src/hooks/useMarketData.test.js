import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import { isNSEMarketOpen } from './useMarketData';

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
