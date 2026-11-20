import numpy as np
import pandas as pd

from quant.market_regime import MarketRegimeClassifier


def _nifty_frame(rows=400, drift=20.0, seed=7, start="2022-01-01"):
    """Synthetic NIFTY-like daily frame with a clean, unambiguous trend."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start, periods=rows, freq="B")
    close = 20000 + np.cumsum(np.full(rows, drift) + rng.normal(0, 3, rows))
    high = close + rng.uniform(0, 6, rows)
    low = close - rng.uniform(0, 6, rows)
    return pd.DataFrame(
        {
            "Open": close,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": rng.integers(1e6, 5e6, rows),
        },
        index=idx,
    )


def _bear_frame(rows=400):
    return _nifty_frame(rows, drift=-20.0, seed=11)


def _classifier_with(frame):
    cls = MarketRegimeClassifier(lookback_bars=260)
    cls._df = frame
    return cls


class TestClassification:
    def test_trending_bullish_uptrend(self):
        res = _classifier_with(_nifty_frame()).classify_regime()
        assert res["regime"] == "TRENDING_BULLISH"
        assert res["nifty_above_ema50"] is True
        assert res["nifty_close"] is not None

    def test_trending_bearish_downtrend(self):
        res = _classifier_with(_bear_frame()).classify_regime()
        assert res["regime"] == "TRENDING_BEARISH"
        assert res["nifty_above_ema50"] is False

    def test_volatility_blowout_labeled_volatile(self):
        # calm drift, then 20 bars of violent mean-reverting chop: the recent
        # 20d realized vol must dwarf the 60d baseline
        calm = _nifty_frame(rows=200, drift=2.0, seed=3)
        level = calm["Close"].iloc[-1]
        swing = level + np.where(np.arange(20) % 2 == 0, 36.0, 0.0)
        idx = pd.date_range(calm.index[-1] + pd.offsets.BDay(), periods=20, freq="B")
        wild = pd.DataFrame(
            {
                "Open": swing,
                "High": swing + 20,
                "Low": swing - 20,
                "Close": swing,
                "Volume": np.full(20, 2e6),
            },
            index=idx,
        )
        res = _classifier_with(pd.concat([calm, wild]).sort_index()).classify_regime()
        assert res["regime"] == "VOLATILE"

    def test_unclear_without_data(self, monkeypatch):
        cls = MarketRegimeClassifier()
        cls._df = None
        # no data source available at all
        monkeypatch.setattr(cls, "load_data", lambda *a, **k: None)
        res = cls.classify_regime()
        assert res["regime"] == "UNCLEAR"
        assert res["nifty_above_ema50"] is None

    def test_unclear_with_short_history(self):
        res = _classifier_with(_nifty_frame(rows=50)).classify_regime()
        assert res["regime"] == "UNCLEAR"


class TestDataSourcing:
    def test_load_data_reuses_merged_history(self, monkeypatch):
        frame = _nifty_frame(rows=300)
        import strategy_tournament

        monkeypatch.setattr(
            strategy_tournament, "_merged_dataset_frames", lambda: [("NIFTY_50_INDEX", frame)]
        )
        cls = MarketRegimeClassifier()
        df = cls.load_data()
        assert df is not None and len(df) > 0
        # second call must hit the cache (no re-scan)
        monkeypatch.setattr(
            strategy_tournament, "_merged_dataset_frames", lambda: (_ for _ in ()).throw(AssertionError("re-scanned"))
        )
        assert cls.load_data() is df

    def test_force_refresh_reruns(self, monkeypatch):
        frame = _nifty_frame(rows=300)
        import strategy_tournament

        calls = {"n": 0}

        def fake_merge():
            calls["n"] += 1
            return [("NIFTY_50_INDEX", frame)]

        monkeypatch.setattr(strategy_tournament, "_merged_dataset_frames", fake_merge)
        cls = MarketRegimeClassifier()
        cls.load_data()
        cls.load_data(force_refresh=True)
        assert calls["n"] == 2

    def test_classifier_contract_keys(self):
        import re

        res = _classifier_with(_nifty_frame()).classify_regime()
        expected = {"regime", "nifty_above_ema50", "nifty_close", "nifty_ema20",
                    "nifty_ema50", "nifty_vol_ratio_20_60", "computed_at"}
        assert expected.issubset(res.keys())
        assert re.match(r"^[\d\-T:.+]+$|^\d{4}-", str(res["computed_at"]))
