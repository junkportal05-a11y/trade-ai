import { describe, it, expect } from 'vitest';
import {
  formatPercent,
  formatRatio,
  getConfidenceScore,
  normalizePerformanceStats,
} from './performance';

describe('normalizePerformanceStats', () => {
  it('uses resolved predictions as total trades and keeps avg win/loss', () => {
    const { source, stats } = normalizePerformanceStats({
      total_predictions: 10,
      resolved_predictions: 3,
      win_rate: 66.7,
      profit_factor: 2.1,
      avg_win: 1.8,
      avg_loss: 0.9,
      expected_value_pct: 0.7,
    });

    expect(source).toBe('live');
    expect(stats.total_trades).toBe(3);
    expect(stats.total_predictions).toBe(10);
    expect(stats.avg_winner).toBe(1.8);
    expect(stats.avg_loser).toBe(0.9);
  });

  it('does not treat unresolved predictions as trades or show misleading zeros', () => {
    const { source, stats } = normalizePerformanceStats({
      total_predictions: 10,
      resolved_predictions: 0,
      win_rate: 0,
      profit_factor: 0,
    });

    expect(source).toBe('simulated');
    expect(stats.total_trades).toBe(0);
    expect(stats.win_rate).toBeNull();
    expect(stats.profit_factor).toBeNull();
    expect(stats.avg_winner).toBeNull();
    expect(stats.avg_loser).toBeNull();
    expect(stats.expectancy).toBeNull();
  });

  it('keeps missing avg_win/avg_loss as null rather than zero', () => {
    const { stats } = normalizePerformanceStats({ total_predictions: 2, resolved_predictions: 2 });

    expect(stats.avg_winner).toBeNull();
    expect(stats.avg_loser).toBeNull();
  });
});

describe('getConfidenceScore', () => {
  it('returns the backend score', () => {
    expect(getConfidenceScore({ overall_confidence: 88 })).toBe(88);
    expect(getConfidenceScore({ confidence_score: 0 })).toBe(0);
  });

  it('returns null instead of inventing 92 when the score is absent', () => {
    expect(getConfidenceScore({})).toBeNull();
    expect(getConfidenceScore(null)).toBeNull();
    expect(getConfidenceScore({ confidence_score: 'nope' })).toBeNull();
  });
});

describe('metric formatting', () => {
  it('renders unknown values as an em dash', () => {
    expect(formatPercent(null)).toBe('—');
    expect(formatRatio(undefined)).toBe('—');
    expect(formatPercent(66.67)).toBe('66.7%');
    expect(formatRatio(2.1)).toBe('2.10x');
  });
});
