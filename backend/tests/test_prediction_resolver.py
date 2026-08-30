import pytest

from trading_agent import resolve_price_decision

def test_target_hit():
    # BUY direction, price above target -> ("TARGET_HIT", "TARGET_HIT")
    direction = "BUY"
    entry_price = 100.0
    stop_loss = 90.0
    target_price = 110.0
    current_price = 115.0  # above target

    status, reason = resolve_price_decision(direction, entry_price, stop_loss, target_price, current_price)
    assert status == "TARGET_HIT"
    assert reason == "TARGET_HIT"

def test_stop_hit():
    # BUY direction, price below stop -> ("STOP_HIT", "STOP_LOSS_HIT")
    direction = "BUY"
    entry_price = 100.0
    stop_loss = 90.0
    target_price = 110.0
    current_price = 85.0  # below stop

    status, reason = resolve_price_decision(direction, entry_price, stop_loss, target_price, current_price)
    assert status == "STOP_HIT"
    assert reason == "STOP_LOSS_HIT"

def test_both_hit_stop_wins():
    # BUY direction, price that would hit both target and stop -> ("STOP_HIT", "STOP_LOSS_HIT")
    direction = "BUY"
    entry_price = 100.0
    stop_loss = 90.0
    target_price = 110.0
    current_price = 85.0  # hits stop first

    status, reason = resolve_price_decision(direction, entry_price, stop_loss, target_price, current_price)
    assert status == "STOP_HIT"
    assert reason == "STOP_LOSS_HIT"

def test_no_hit():
    # BUY direction, price between target and stop -> (None, None)
    direction = "BUY"
    entry_price = 100.0
    stop_loss = 90.0
    target_price = 110.0
    current_price = 95.0  # between stop and target

    status, reason = resolve_price_decision(direction, entry_price, stop_loss, target_price, current_price)
    assert status is None
    assert reason is None

def test_sell_target_hit():
    # SELL direction, price below target -> ("TARGET_HIT", "TARGET_HIT")
    direction = "SELL"
    entry_price = 100.0
    stop_loss = 90.0
    target_price = 80.0  # target is below current
    current_price = 75.0  # below target

    status, reason = resolve_price_decision(direction, entry_price, stop_loss, target_price, current_price)
    assert status == "TARGET_HIT"
    assert reason == "TARGET_HIT"

def test_sell_stop_hit():
    # SELL direction, price above stop -> ("STOP_HIT", "STOP_LOSS_HIT")
    direction = "SELL"
    entry_price = 100.0
    stop_loss = 90.0
    target_price = 80.0
    current_price = 95.0  # above stop

    status, reason = resolve_price_decision(direction, entry_price, stop_loss, target_price, current_price)
    assert status == "STOP_HIT"
    assert reason == "STOP_LOSS_HIT"

def test_sell_both_hit_stop_wins():
    # SELL direction, price that hits both -> ("STOP_HIT", "STOP_LOSS_HIT")
    direction = "SELL"
    entry_price = 100.0
    stop_loss = 90.0
    target_price = 80.0
    current_price = 95.0  # hits stop first

    status, reason = resolve_price_decision(direction, entry_price, stop_loss, target_price, current_price)
    assert status == "STOP_HIT"
    assert reason == "STOP_LOSS_HIT"