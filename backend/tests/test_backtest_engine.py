import numpy as np
import pandas as pd

import backend.backtest_engine as bt
from backend.backtest_engine import (
    BacktestConfig,
    resolve_candle_pessimistic,
    run_historical_backtest,
)


def _make_df(rows=200, start="2020-01-01", seed=42):
    """Synthetic OHLCV frame with capitalised columns and a DatetimeIndex."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start, periods=rows, freq="D")
    # Random walk close so indicators have something to chew on
    close = 100 + np.cumsum(rng.normal(0, 1, rows))
    high = close + rng.uniform(0, 2, rows)
    low = close - rng.uniform(0, 2, rows)
    open_ = close + rng.normal(0, 0.5, rows)
    volume = rng.integers(1_000, 5_000, rows)
    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": volume,
        },
        index=idx,
    )


def test_backtestconfig_has_adx_min():
    cfg = BacktestConfig(period_range="1y", entry_score=3, adx_min=25)
    assert cfg.adx_min == 25
    assert cfg.period_range == "1y"
    assert cfg.entry_score == 3


def test_resolve_candle_pessimistic_stop_priority():
    # Both target and stop touched in same candle -> stop wins (pessimistic)
    candle = {"high": 110, "low": 90, "open": 100}
    result, exit_p = resolve_candle_pessimistic(
        candle, entry=100, target=110, stop=90, direction="BUY"
    )
    assert result == "LOSS"
    assert exit_p == 90


def test_resolve_candle_pessimistic_win():
    candle = {"high": 115, "low": 95, "open": 100}
    result, exit_p = resolve_candle_pessimistic(
        candle, entry=100, target=110, stop=90, direction="BUY"
    )
    assert result == "WIN"
    assert exit_p == 110


def test_resolve_candle_pessimistic_no_touch():
    candle = {"high": 104, "low": 96, "open": 100}
    result, exit_p = resolve_candle_pessimistic(
        candle, entry=100, target=110, stop=90, direction="BUY"
    )
    assert result is None
    assert exit_p is None


def test_compute_indicators_adds_columns():
    df = _make_df(rows=60)
    out = bt._compute_indicators(df)
    for col in ("ATR", "RSI", "ADX", "SMA50"):
        assert col in out.columns
    # After warm-up window, values should be finite (no NaN at the tail)
    assert np.isfinite(out["ATR"].iloc[-1])
    assert np.isfinite(out["RSI"].iloc[-1])
    assert np.isfinite(out["ADX"].iloc[-1])


def test_calculate_daily_score_ranges():
    df = _make_df(rows=60)
    df = bt._compute_indicators(df)
    # Score is an int and within a sane band
    s = bt._calculate_daily_score(df, 59)
    assert isinstance(s, int)
    assert -10 <= s <= 10


def test_run_backtest_insufficient_data(monkeypatch):
    def mock_none(*args, **kwargs):
        return None

    # The function imports: from signals import download_market_data_df
    monkeypatch.setattr(
        "signals.download_market_data_df", mock_none
    )
    # Also mock the CSV file check to return False
    monkeypatch.setattr("os.path.exists", lambda x: False)
    # Avoid any AngelOne network/auth calls
    class FakeFeed:
        def is_session_valid(self):
            return True

        def auto_login(self):
            return True

    monkeypatch.setattr("backend.angelone_feed.AngelOneFeed", FakeFeed)

    result = run_historical_backtest("RELIANCE", BacktestConfig(period_range="1mo"))
    assert "error" in result


def test_run_backtest_with_mock_data(monkeypatch):
    def mock_df(*args, **kwargs):
        return _make_df(rows=200)

    monkeypatch.setattr(
        "backend.backtest_engine.download_market_data_df", mock_df
    )

    class FakeFeed:
        def is_session_valid(self):
            return True

        def auto_login(self):
            return True

    monkeypatch.setattr("backend.angelone_feed.AngelOneFeed", FakeFeed)

    result = run_historical_backtest(
        "RELIANCE", BacktestConfig(period_range="2y", entry_score=3, adx_min=25)
    )

    # No error and we get the expected summary keys
    assert "error" not in result, result
    assert result["symbol"] == "RELIANCE"
    assert isinstance(result["total_trades"], int)
    assert isinstance(result["trades"], list)
    assert "equity_curve" in result
    # Stats are internally consistent with the raw trade list
    trades = result["trades"]
    assert result["total_trades"] == len(trades)
    assert result["wins"] == len([t for t in trades if t["pnl"] > 0])
    assert result["losses"] == len([t for t in trades if t["pnl"] < 0])
    assert result["win_rate"] == round(
        (result["wins"] / result["total_trades"]) * 100, 1
    ) if result["total_trades"] > 0 else 0.0
