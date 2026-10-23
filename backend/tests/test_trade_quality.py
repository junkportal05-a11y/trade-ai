import pytest
from trade_quality import TradeQualityEngine

def test_trade_quality_unclear_rejects():
    # Base confidence 80
    result = TradeQualityEngine.calculate_tqs(
        confidence_score=80.0,
        is_long=True,
        regime="UNCLEAR",
        volatility=0.0,
        volume_expansion=1.0
    )
    # 80 - 25 = 55. 55 < 72, so REJECT.
    assert result["score"] == 55.0
    assert result["classification"] == "REJECT"

def test_trade_quality_trending_reaches_elite():
    # Base confidence 85
    result = TradeQualityEngine.calculate_tqs(
        confidence_score=85.0,
        is_long=True,
        regime="TRENDING",
        volatility=0.0,
        volume_expansion=1.0
    )
    # 85 + 10 = 95. 95 >= 90, so ELITE_CANDIDATE
    assert result["score"] == 95.0
    assert result["classification"] == "ELITE_CANDIDATE"
