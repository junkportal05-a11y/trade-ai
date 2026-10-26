const toNumberOrNull = (value) => {
  if (value === null || value === undefined || value === '') return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

// The backend /api/data/confidence response is the only source of this score.
// Never invent a passing default: a missing score means "unknown", not 92.
export function getConfidenceScore(data) {
  if (!data) return null;
  return toNumberOrNull(data.overall_confidence ?? data.confidence_score);
}

export function normalizePerformanceStats(data) {
  const resolved = toNumberOrNull(data?.resolved_predictions) ?? 0;
  const totalPredictions = toNumberOrNull(data?.total_predictions) ?? 0;
  const hasResolved = resolved > 0;

  return {
    source: hasResolved ? 'live' : 'simulated',
    stats: {
      total_trades: resolved,
      total_predictions: totalPredictions,
      win_rate: hasResolved ? toNumberOrNull(data?.win_rate) : null,
      profit_factor: hasResolved ? toNumberOrNull(data?.profit_factor) : null,
      avg_winner: hasResolved ? toNumberOrNull(data?.avg_win) : null,
      avg_loser: hasResolved ? toNumberOrNull(data?.avg_loss) : null,
      expectancy: hasResolved ? toNumberOrNull(data?.expected_value_pct) : null,
      empirical_rr: hasResolved ? toNumberOrNull(data?.empirical_rr_ratio) : null,
      max_drawdown: hasResolved ? toNumberOrNull(data?.max_drawdown_pct) : null,
    },
  };
}

export function formatPercent(value, digits = 1) {
  return value == null ? '—' : `${Number(value).toFixed(digits)}%`;
}

export function formatRatio(value, digits = 2) {
  return value == null ? '—' : `${Number(value).toFixed(digits)}x`;
}
