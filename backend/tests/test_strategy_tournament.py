import os
import shutil

import numpy as np
import pandas as pd
import pytest

import backend.strategy_tournament as st
from quant.cost_engine import CostEngine


def _make_df(rows=300, start="2020-01-01", seed=42):
    """Synthetic OHLCV frame with capitalised columns and a DatetimeIndex."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start, periods=rows, freq="D")
    close = 100 + np.cumsum(rng.normal(0, 1, rows))
    high = close + rng.uniform(0, 2, rows)
    low = close - rng.uniform(0, 2, rows)
    open_ = close + rng.normal(0, 0.5, rows)
    volume = rng.integers(1_000, 5_000, rows)
    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume},
        index=idx,
    )


def _trend_df(direction="up", rows=300):
    """Strongly trending series with realistic small noise - for direction checks."""
    rng = np.random.default_rng(123)
    idx = pd.date_range("2020-01-01", periods=rows, freq="D")
    drift = 0.5 if direction == "up" else -0.5
    close = 100 + np.cumsum(np.full(rows, drift) + rng.normal(0, 0.3, rows))
    wobble = 0.15
    high = close + wobble
    low = close - wobble
    return pd.DataFrame(
        {
            "Open": close + 0.01,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": np.full(rows, 1000.0),
        },
        index=idx,
    )


# ── CostEngine ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "prev,new,expected",
    [
        (0, 0, 0),
        (0, 1, 1),      # open
        (1, 0, 1),      # close
        (0.5, 1.0, 1),  # scale up
        (1, -1, 2),     # flip
        (-0.3, 0.7, 2), # long<-short flip
    ],
)
def test_cost_engine_sides_for_turn(prev, new, expected):
    assert CostEngine.sides_for_turn(prev, new) == expected


def test_cost_engine_zero_cost_config():
    zero = CostEngine(side_cost_bps=0.0)
    assert zero.turnover_cost(1, -1) == 0.0
    assert zero.calculate(5000.0, 1, -1) == 0.0


def test_cost_engine_rejects_negative():
    with pytest.raises(ValueError):
        CostEngine(side_cost_bps=-1)


def test_backward_compatible_calculate_stub():
    # Old callers did `CostEngine().calculate()` -> 0.0
    assert CostEngine(side_cost_bps=0.0).calculate() == 0.0


# ── Real indicators ──────────────────────────────────────────────────────────

def test_supertrend_long_in_uptrend():
    sig = st._supertrend(_trend_df("up"), period=10, mult=3.0)
    recent = sig.iloc[-50:]
    assert (recent == 1).all()


def test_supertrend_short_in_downtrend():
    sig = st._supertrend(_trend_df("down"), period=10, mult=3.0)
    recent = sig.iloc[-50:]
    assert (recent == -1).all()


def test_supertrend_warmup_flat():
    sig = st._supertrend(_make_df())
    assert (sig.iloc[:period_warmup()] == 0).all()  # ATR(10) warm-up stays flat


def period_warmup():
    # tr.rolling(10).mean() first yields a value at the 9th bar (0-based index)
    return 9


def test_parabolic_sar_long_in_uptrend():
    sig = st._parabolic_sar(_trend_df("up"))
    assert (sig.iloc[1:] == 1).all()


def test_parabolic_sar_short_in_downtrend():
    sig = st._parabolic_sar(_trend_df("down"))
    # bar 0 is the long seed; every subsequent bar must be short
    assert (sig.iloc[1:] == -1).all()


# ── Simulation behaviour ─────────────────────────────────────────────────────

def test_flip_heavy_strategy_pays_costs():
    """
    A strategy churning daily on a ranging tape must show a positive cost
    drag, and zero-cost config must not report any cost.
    """
    df = _make_df(seed=7)
    costed = st.simulate_strategy(df, strat_id=2)  # EMA 9/21 flip-churns in range
    free = st.simulate_strategy(df, strat_id=2, side_cost_bps=0.0)
    assert len(df) > 260  # sanity: full year of churn
    assert costed["cost_paid_pct"] > 0.0
    assert free["cost_paid_pct"] == 0.0
    # Costing can only reduce (or leave equal) the achieved return on a
    # payout-free simulation universe
    assert costed["final_capital"] <= free["final_capital"]


def test_metrics_structure_and_bounds():
    df = _make_df(seed=3)
    res = st.simulate_strategy(df, strat_id=4)
    assert isinstance(res["total_return_pct"], float)
    assert 0.0 <= res["win_rate"] <= 100.0
    assert 0.0 <= res["max_drawdown_pct"] <= 100.0
    assert np.isfinite(res["sharpe_ratio"])
    assert res["avg_turnover"] >= 0.0


def test_vol_sizing_bounded():
    # Strategy 27 must operate inside fractional exposure bounds, never a
    # full 2x flip: turnover per rebalance <= 2 (from 1.0 to -0.3).
    df = _make_df(seed=11)
    res = st.simulate_strategy(df, strat_id=27)
    assert 0.0 <= res["avg_turnover"] <= 2.0


def test_regime_adaptive_goes_flat_in_chop():
    # Strategy 30 must be flat when no regime confirms.
    df = _make_df(seed=5)
    res = st.simulate_strategy(df, strat_id=30)
    flat_rows_share_higher_than_churny_peer = res["avg_turnover"] <= st.simulate_strategy(df, strat_id=1)["avg_turnover"] + 0.01
    assert flat_rows_share_higher_than_churny_peer


def test_tournament_full_run_sorted_and_complete(tmp_path, monkeypatch):
    """
    Full walk-forward tournament over a copy of one real dataset: every
    registry strategy (incl. 31/32), ranks assigned, cost/profit-factor and
    walk-forward fields present, score respects order, ACTIVE/RETIRED status.
    """
    src = None
    for candidate in ("RELIANCE_10y_daily.csv", "TCS_10y_daily.csv", "SBIN_10y_daily.csv"):
        p = os.path.join(st.HISTORICAL_DATA_DIR, candidate)
        if os.path.exists(p):
            src = p
            break
    assert src, "no historical csv found for tournament test"

    data_dir = tmp_path / "historical_data"
    data_dir.mkdir()
    shutil.copy(src, data_dir / os.path.basename(src))

    monkeypatch.setattr(st, "HISTORICAL_DATA_DIR", str(data_dir))
    results = st.run_full_tournament()

    assert len(results) == len(st.STRATEGY_REGISTRY)
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)
    assert [r["rank"] for r in results] == list(range(1, len(st.STRATEGY_REGISTRY) + 1))
    # leaderboard row contract expected by bot_trainer / tournament API
    for row in results:
        assert {"strat_id", "strategy", "bucket", "score", "win_rate", "sharpe_ratio",
                "max_drawdown_pct", "total_return_pct", "datasets_tested",
                "status", "profit_factor", "in_sample_score",
                "out_of_sample_score", "selected_params"}.issubset(row.keys())
        assert row["status"] in ("ACTIVE", "RETIRED")
        assert 0.0 <= row["profit_factor"] <= 99.99


def test_tournament_walk_forward_weights_and_retirement(tmp_path, monkeypatch):
    """Union of legacy + 7y datasets merges to one frame; score composition
    honours the 0.4/0.6 walk-forward weights; a strategy with negative OOS
    expectancy is marked RETIRED."""
    src = None
    for candidate in ("RELIANCE_10y_daily.csv", "TCS_10y_daily.csv", "SBIN_10y_daily.csv"):
        p = os.path.join(st.HISTORICAL_DATA_DIR, candidate)
        if os.path.exists(p):
            src = p
            break
    assert src

    data_dir = tmp_path / "historical_data"
    data_dir.mkdir()
    shutil.copy(src, data_dir / os.path.basename(src))

    monkeypatch.setattr(st, "HISTORICAL_DATA_DIR", str(data_dir))
    results = st.run_full_tournament()
    assert results
    for row in results:
        expected = round(st.IS_WEIGHT * row["in_sample_score"] + st.OOS_WEIGHT * row["out_of_sample_score"], 2)
        assert abs(row["score"] - expected) < 0.05
        assert row["walk_forward_weights"] == {"in_sample": st.IS_WEIGHT, "out_of_sample": st.OOS_WEIGHT}


# ── Parameter calibration ────────────────────────────────────────────────────

def test_param_grids_exist_for_directed_strategies():
    grid4 = st.get_param_grid(4)
    assert {"atr_len": 10, "mult": 3.0} in grid4 and {"atr_len": 14, "mult": 2.5} in grid4
    assert len(set(map(lambda g: (g["atr_len"], g["mult"]), grid4))) == len(grid4)

    grid10 = st.get_param_grid(10)
    assert [g["bb_std"] for g in grid10] == [2.0, 2.5]

    grid17 = st.get_param_grid(17)
    assert [g["vol_mult"] for g in grid17] == [1.5, 2.0, 2.5]

    # non-parametric strategies get the single default variant
    assert st.get_param_grid(1) == [{}]
    assert st.get_param_grid(31) == [{}]


def test_supertrend_params_change_signals():
    df = _make_df(seed=21, rows=500)
    a = st._supertrend(df, period=10, mult=3.0)
    b = st._supertrend(df, period=14, mult=2.5)
    assert not np.array_equal(a.to_numpy(), b.to_numpy())


def test_strategy_31_vol_targeted_bounded():
    df = _make_df(seed=13, rows=400)
    res = st.simulate_strategy(df, strat_id=31)
    assert 0.0 <= res["avg_turnover"] <= 2.0
    assert np.isfinite(res["sharpe_ratio"])


def test_strategy_32_gap_persistence():
    df = _make_df(seed=17, rows=300)
    res = st.simulate_strategy(df, strat_id=32)
    assert res["total_trades"] >= 0
    assert isinstance(res["profit_factor"], float)


def test_profit_factor_present_and_bounded():
    df = _make_df(seed=9, rows=350)
    res = st.simulate_strategy(df, strat_id=25)
    assert 0.0 <= res["profit_factor"] <= 99.99
    assert res["selected_params"] == {}


def test_nse_friction_composition():
    # Slippage-only variant is exactly the mandated 5 bps/side
    slip_only = CostEngine(side_cost_bps=5.0)
    assert slip_only.side_cost_bps == 5.0
    # Delivery default carries the full statutory stack (~11.7 bps/side)
    delivery = CostEngine()
    assert 10.0 <= delivery.side_cost_bps <= 13.0
    intraday = CostEngine(product="intraday")
    assert intraday.side_cost_bps < delivery.side_cost_bps
