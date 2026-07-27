import { describe, it, expect } from 'vitest';
import { calcMACD } from './indicators';

describe('calcMACD', () => {
  it('returns empty lines when data is empty', () => {
    const result = calcMACD([]);
    expect(result).toEqual({ macdLine: [], signalLine: [], histogram: [] });
  });

  it('returns empty lines when data is null', () => {
    const result = calcMACD(null);
    expect(result).toEqual({ macdLine: [], signalLine: [], histogram: [] });
  });

  it('calculates MACD correctly for constant data', () => {
    const data = Array.from({ length: 50 }, (_, i) => ({ time: i, close: 100 }));
    const result = calcMACD(data);

    expect(result.macdLine).toHaveLength(50);
    expect(result.signalLine).toHaveLength(50);
    expect(result.histogram).toHaveLength(50);

    expect(result.macdLine[49].value).toBeCloseTo(0);
    expect(result.signalLine[49].value).toBeCloseTo(0);
    expect(result.histogram[49].value).toBeCloseTo(0);
  });

  it('calculates MACD correctly for an uptrend', () => {
    const data = Array.from({ length: 50 }, (_, i) => ({ time: i, close: 10 + i * 2 }));
    const result = calcMACD(data);

    expect(result.macdLine).toHaveLength(50);
    expect(result.signalLine).toHaveLength(50);
    expect(result.histogram).toHaveLength(50);

    expect(result.macdLine[49].value).toBeGreaterThan(0);
    expect(result.histogram[49].value).toBeGreaterThan(0);
  });

  it('calculates MACD correctly for a downtrend', () => {
    const data = Array.from({ length: 50 }, (_, i) => ({ time: i, close: 100 - i * 2 }));
    const result = calcMACD(data);

    expect(result.macdLine[49].value).toBeLessThan(0);
    expect(result.histogram[49].value).toBeLessThan(0);
  });

  it('supports custom fast, slow, and signal periods', () => {
    const data = Array.from({ length: 30 }, (_, i) => ({ time: i, close: 10 + i * 2 }));
    const result = calcMACD(data, 5, 10, 3);

    expect(result.macdLine).toHaveLength(30);
    expect(result.signalLine).toHaveLength(30);
    expect(result.histogram).toHaveLength(30);
  });

  it('handles small amount of data gracefully', () => {
    const data = [{ time: 1, close: 100 }];
    const result = calcMACD(data);

    expect(result.macdLine).toHaveLength(1);
    expect(result.signalLine).toHaveLength(1);
    expect(result.histogram).toHaveLength(1);

    expect(result.macdLine[0].value).toBe(0);
    expect(result.signalLine[0].value).toBe(0);
    expect(result.histogram[0].value).toBe(0);
  });
});
