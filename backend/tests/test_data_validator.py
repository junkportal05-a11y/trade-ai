from data_validator import validate_trade, calculate_confidence_from_counts

def test_validate_trade_happy_path_open():
    trade = {
        "entry_price": 100.0,
        "target": 120.0,
        "stop_loss": 90.0,
        "direction": "BUY",
        "status": "OPEN",
        "market_regime_snapshot": "BULL_TREND",
        "created_at": "2023-01-01T10:00:00"
    }
    result = validate_trade(trade)
    assert result["valid"] is True
    assert result["score"] == 100
    assert len(result["failures"]) == 0

def test_validate_trade_happy_path_resolved():
    trade = {
        "entry_price": 100.0,
        "target": 120.0,
        "stop_loss": 90.0,
        "signal_type": "BUY",
        "status": "WIN",
        "exit_price": 120.0,
        "pnl": 20.0,
        "market_regime_snapshot": "BULL_TREND",
        "created_at": "2023-01-01T10:00:00",
        "resolved_at": "2023-01-01T11:00:00"
    }
    result = validate_trade(trade)
    assert result["valid"] is True

def test_validate_trade_invalid_entry_price():
    trade = {"status": "OPEN", "market_regime_snapshot": "BULL_TREND"}
    result = validate_trade(trade)
    assert result["valid"] is False
    assert "entry_price is null" in result["failures"]

    trade["entry_price"] = 0
    result = validate_trade(trade)
    assert "entry_price <= 0" in result["failures"]

def test_validate_trade_invalid_buy_direction():
    trade = {
        "entry_price": 100.0,
        "target": 90.0,
        "stop_loss": 110.0,
        "prediction_type": "BUY",
        "status": "OPEN",
        "market_regime_snapshot": "BULL_TREND"
    }
    result = validate_trade(trade)
    assert "stop_loss >= entry_price (BUY)" in result["failures"]
    assert "target <= entry_price (BUY)" in result["failures"]

def test_validate_trade_invalid_sell_direction():
    trade = {
        "entry_price": 100.0,
        "target": 110.0,
        "stop_loss": 90.0,
        "prediction_type": "SELL",
        "status": "OPEN",
        "market_regime_snapshot": "BEAR_TREND"
    }
    result = validate_trade(trade)
    assert "stop_loss <= entry_price (SELL)" in result["failures"]
    assert "target >= entry_price (SELL)" in result["failures"]

def test_validate_trade_invalid_dates():
    trade = {
        "entry_price": 100.0,
        "status": "OPEN",
        "market_regime_snapshot": "BULL_TREND",
        "created_at": "2023-01-02T10:00:00",
        "resolved_at": "2023-01-01T10:00:00"
    }
    result = validate_trade(trade)
    assert "resolved_at <= created_at" in result["failures"]

def test_validate_trade_invalid_status():
    trade = {
        "entry_price": 100.0,
        "status": "UNKNOWN_STATUS",
        "market_regime_snapshot": "BULL_TREND"
    }
    result = validate_trade(trade)
    assert "result is not one of" in result["failures"][0]

    # Real resolution statuses written by the bot/manual endpoints are valid
    trade["status"] = "TARGET_HIT"
    result = validate_trade(trade)
    assert not any(f.startswith("result is not one of") for f in result["failures"])

def test_validate_trade_invalid_resolved_trade():
    # WIN without exit price
    trade = {
        "entry_price": 100.0,
        "status": "WIN",
        "market_regime_snapshot": "BULL_TREND",
        "pnl": 10.0
    }
    result = validate_trade(trade)
    assert "exit_price missing or <= 0 for resolved trade" in result["failures"]

    # WIN with negative pnl
    trade["exit_price"] = 110.0
    trade["pnl"] = -10.0
    result = validate_trade(trade)
    assert "WIN status but PnL <= 0" in result["failures"]

    # LOSS with positive pnl
    trade["status"] = "LOSS"
    trade["pnl"] = 10.0
    result = validate_trade(trade)
    assert "LOSS status but PnL >= 0" in result["failures"]

def test_validate_trade_invalid_regime():
    trade = {"entry_price": 100.0, "status": "OPEN"}
    result = validate_trade(trade)
    assert "regime is null or UNKNOWN" in result["failures"]

    # UNCLEAR means the classifier has no data — a warning, not a data defect
    trade["market_regime_snapshot"] = "UNCLEAR"
    result = validate_trade(trade)
    assert not result["failures"]
    assert "regime is UNCLEAR (classifier unavailable)" in result["warnings"]

    trade["market_regime_snapshot"] = "UNKNOWN"
    result = validate_trade(trade)
    assert "regime is null or UNKNOWN" in result["failures"]

def test_validate_trade_score_calculation():
    trade = {
        "entry_price": -10.0, # 1
        "status": "BAD", # 2
        "market_regime_snapshot": "UNKNOWN", # 3
        "created_at": "2023-01-02",
        "resolved_at": "2023-01-01", # 4
        "prediction_type": "BUY",
        "stop_loss": 100.0, # 5
        "target": -20.0 # 6
    }
    result = validate_trade(trade)
    # 6 failures, each -20 -> caps at 0
    assert len(result["failures"]) == 6
    assert result["score"] == 0
    assert result["valid"] is False


def test_confidence_calculation():
    score = calculate_confidence_from_counts(valid=85, total=100)
    assert score == 85.0


def test_confidence_zero_trades_does_not_crash():
    score = calculate_confidence_from_counts(valid=0, total=0)
    assert score == 0.0
