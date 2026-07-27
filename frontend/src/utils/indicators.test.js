import { describe, it, expect } from 'vitest';
import { calcEMA } from './indicators.js';

describe('calcEMA', () => {
  it('should return an empty array if data is empty', () => {
    expect(calcEMA([], 3)).toEqual([]);
  });

  it('should handle a single data point', () => {
    const data = [{ time: 1, close: 10 }];
    expect(calcEMA(data, 3)).toEqual([{ time: 1, value: 10 }]);
  });

  it('should correctly calculate EMA for multiple data points', () => {
    const data = [
      { time: 1, close: 10 },
      { time: 2, close: 20 },
      { time: 3, close: 30 }
    ];
    // period = 3, k = 2 / (3 + 1) = 0.5
    // EMA1 = 10
    // EMA2 = 20 * 0.5 + 10 * 0.5 = 15
    // EMA3 = 30 * 0.5 + 15 * 0.5 = 22.5
    const expected = [
      { time: 1, value: 10 },
      { time: 2, value: 15 },
      { time: 3, value: 22.5 }
    ];
    expect(calcEMA(data, 3)).toEqual(expected);
  });
});
