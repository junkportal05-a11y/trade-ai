"""
capital_allocator.py  —  HIGH RETURN NSE Intraday Allocator
============================================================
Goal: 10-20% return on capital per trade session.

Strategy:
  - Target stocks with ATR > 2% of price (moves ₹10-50+ per day)
  - Minimum profit target = 10% of capital invested in that stock
  - Only stocks where 1 lot / 1 share gives meaningful profit
  - Prefer stocks ₹50-₹800 range (affordable + high % moves)
  - Avoid ₹2000+ stocks for small capital (profit too small per share)
  - Use confidence + ATR% + volume surge as combined score
"""


def generate_mentor_advice(
    sig: dict, actual_cost: float, pot_loss: float, capital: float, rr: float
) -> list:
    advice = []

    # 1. Candlestick check from Candlestick Bible
    candlestick_found = False
    reasons = sig.get("reasons", [])
    for r in reasons:
        if "Hammer" in r:
            advice.append(
                "✦ Candlestick Bible: Hammer detected! This shows buyers rejected lower prices and took control. Wait for the next candle to break the high for confirmation."
            )
            candlestick_found = True
            break
        elif "Shooting Star" in r:
            advice.append(
                "✦ Candlestick Bible: Shooting Star detected! Selling pressure pushes prices down. Keep stop loss tight above the high wick."
            )
            candlestick_found = True
            break
        elif "Engulfing" in r:
            advice.append(
                "✦ Candlestick Bible: Engulfing Pattern detected! Shows a powerful shift in momentum. Buy engulfing suggests buyers have overwhelmed sellers completely."
            )
            candlestick_found = True
            break
        elif "Marubozu" in r:
            advice.append(
                "✦ Candlestick Bible: Marubozu detected! A full solid body shows extreme buying strength. Momentum is highly likely to continue higher."
            )
            candlestick_found = True
            break

    if not candlestick_found:
        advice.append(
            "✦ Candlestick Bible: Look for confirmation patterns (like Engulfing or Hammer candles) near moving average supports before entering."
        )

    # 2. Risk sizing check from SL Guide
    risk_pct_of_cap = (pot_loss / capital) * 100 if capital > 0 else 0
    if risk_pct_of_cap <= 2.0:
        advice.append(
            f"✦ Risk Management: Risking ₹{pot_loss:,.1f} ({risk_pct_of_cap:.1f}% of capital). This aligns perfectly with the 1-2% golden risk rule in your SL Guide."
        )
    else:
        advice.append(
            f"✦ Risk Management: Risking ₹{pot_loss:,.1f} ({risk_pct_of_cap:.1f}% of capital). This exceeds the standard 2% rule. Consider scaling down if account size permits."
        )

    # 3. R:R check
    if rr >= 2.0:
        advice.append(
            f"✦ Risk-Reward: R:R ratio is 1:{rr:.2f}. This exceeds your guide's target minimum of 1:2. Excellent trade structure!"
        )
    else:
        advice.append(
            f"✦ Risk-Reward: R:R ratio is 1:{rr:.2f}. Below your guide's ideal 1:2 ratio. Tighten your stop loss or aim for higher targets to improve reward ratios."
        )

    # 4. Stop loss placement advice
    advice.append(
        f"✦ Stop Loss Guide: Place your stop loss strictly below support at ₹{sig.get('stop_loss', 0):,.2f}. Avoid placing it exactly on round numbers to prevent market-maker stop-runs."
    )

    # 5. Flat brokerage warning for small capital
    if capital < 10000:
        advice.append(
            f"✦ Brokerage Alert: With small capital (₹{capital:,.0f}), flat brokerage fees (e.g. ₹20/order) "
            f"will significantly eat into profits. Ensure you use discount brokers or accumulate larger capital for sustainable trading."
        )

    return advice


def _get_tier_config(capital: float, risk: str, max_recommendations: int) -> tuple:
    if capital < 2_000:
        max_positions = 1
        cash_buffer = 0.02
        risk_pct = 0.08
        max_per_stock = 0.98
        min_profit_target = capital * 0.08
    elif capital < 5_000:
        max_positions = 1
        cash_buffer = 0.03
        risk_pct = 0.06
        max_per_stock = 0.97
        min_profit_target = capital * 0.10
    elif capital < 15_000:
        max_positions = 2
        cash_buffer = 0.04
        risk_pct = 0.05
        max_per_stock = 0.65
        min_profit_target = capital * 0.04
    elif capital < 50_000:
        max_positions = 3
        cash_buffer = 0.05
        risk_pct = 0.04
        max_per_stock = 0.45
        min_profit_target = capital * 0.025
    elif capital < 2_00_000:
        max_positions = 4
        cash_buffer = 0.05
        risk_pct = 0.03
        max_per_stock = 0.35
        min_profit_target = capital * 0.02
    else:
        max_positions = 6
        cash_buffer = 0.05
        risk_pct = 0.025
        max_per_stock = 0.25
        min_profit_target = capital * 0.015

    if risk == "Low":
        risk_pct = risk_pct * 0.7
    elif risk == "High":
        risk_pct = risk_pct * 1.3

    max_positions = max(1, min(max_positions, max_recommendations))
    deployable = capital * (1 - cash_buffer)

    return max_positions, deployable, risk_pct, max_per_stock, min_profit_target


def _filter_and_score_signals(signals: list, deployable: float, max_positions: int) -> list:
    candidates = []
    for s in signals:
        raw_signal = s.get("direction") or s.get("signal") or ""
        if "BUY" not in raw_signal.upper():
            continue
        # Only allocate to signals with high confidence
        if s.get("confidence", 0) < 72:
            continue

        entry = s.get("entry") or s.get("entry_price") or s.get("price", 0)
        stop = s.get("stop_loss", 0)
        target = s.get("target", 0)
        atr = s.get("atr", 0)

        if entry <= 0:
            continue
        if stop <= 0 or stop >= entry:
            stop = round(entry * 0.98, 2)
        if target <= 0 or target <= entry:
            target = round(entry * 1.03, 2)
        if entry > deployable:
            continue

        atr_pct = (atr / entry * 100) if entry > 0 else 0
        profit_pct = (target - entry) / entry * 100

        score = s["confidence"] * (1 + atr_pct * 0.3) * (1 + min(profit_pct, 20) * 0.05)

        s = dict(s)
        s["direction"] = "BUY"
        s["entry"] = entry
        s["stop_loss"] = stop
        s["target"] = target
        s["atr_pct"] = round(atr_pct, 2)
        s["profit_pct"] = round(profit_pct, 2)
        s["_score"] = score
        candidates.append(s)

    candidates.sort(key=lambda x: x["_score"], reverse=True)
    return candidates[:max_positions]


def _build_positions(candidates: list, capital: float, deployable: float, max_per_stock: float, risk_pct: float, min_profit_target: float) -> tuple:
    total_score = sum(c["_score"] for c in candidates)
    positions = []
    deployed = 0

    for sig in candidates:
        entry = sig["entry"]
        stop = sig["stop_loss"]

        target1 = sig.get("target1") or sig.get("target") or (entry * 1.03)
        target2 = sig.get("target2") or round(target1 * 1.05, 2)

        weight = sig["_score"] / total_score
        raw_alloc = deployable * weight
        capped_alloc = min(raw_alloc, capital * max_per_stock)
        remaining = deployable - deployed

        budget = min(capped_alloc, remaining)
        if budget < entry * 0.01:
            continue

        risk_per_share = abs(entry - stop)
        max_risk_money = capital * risk_pct

        shares_by_cap = round(budget / entry, 2)
        shares_by_risk = (
            round(max_risk_money / risk_per_share, 2)
            if risk_per_share > 0
            else shares_by_cap
        )
        shares = min(shares_by_risk, shares_by_cap)

        if shares * entry > remaining:
            shares = round(remaining / entry, 2)
        if shares < 0.01:
            continue

        actual_cost = round(shares * entry, 2)
        pot_profit = round(shares * (target1 - entry), 2)
        pot_profit_high = round(shares * (target2 - entry), 2)
        pot_loss = round(shares * (entry - stop), 2)
        rr = round((target1 - entry) / (entry - stop), 2) if (entry - stop) > 0 else 0
        profit_on_inv = (
            round((pot_profit / actual_cost) * 100, 2) if actual_cost > 0 else 0
        )
        profit_on_cap = round((pot_profit / capital) * 100, 2)

        if pot_profit < min_profit_target:
            needed_shares = (
                round(min_profit_target / (target1 - entry), 2)
                if (target1 - entry) > 0
                else shares
            )
            if (
                needed_shares * entry <= remaining
                and (needed_shares * risk_per_share) <= max_risk_money
            ):
                shares = needed_shares
                actual_cost = round(shares * entry, 2)
                pot_profit = round(shares * (target1 - entry), 2)
                pot_profit_high = round(shares * (target2 - entry), 2)
                pot_loss = round(shares * (entry - stop), 2)
                profit_on_inv = (
                    round((pot_profit / actual_cost) * 100, 2) if actual_cost > 0 else 0
                )
                profit_on_cap = round((pot_profit / capital) * 100, 2)

        advice = generate_mentor_advice(sig, actual_cost, pot_loss, capital, rr)

        qty_label = f"{shares} Shares" if shares >= 1 else f"{shares:.2f} Shares"
        estimated_profit = f"₹{pot_profit:.0f} - ₹{pot_profit_high:.0f}"

        positions.append(
            {
                "symbol": sig.get("symbol", ""),
                "direction": "BUY",
                "confidence": sig["confidence"],
                "entry_price": round(entry, 2),
                "target": round(target1, 2),
                "target1": round(target1, 2),
                "target2": round(target2, 2),
                "stop_loss": round(stop, 2),
                "rr_ratio": rr,
                "shares": shares,
                "quantity": shares,
                "quantity_label": qty_label,
                "amount_invested": actual_cost,
                "allocation_pct": round((actual_cost / capital) * 100, 1),
                "potential_profit": pot_profit,
                "potential_profit_high": pot_profit_high,
                "potential_loss": pot_loss,
                "profit_on_invested": profit_on_inv,
                "profit_on_capital": profit_on_cap,
                "atr": round(sig.get("atr", 0), 2),
                "atr_pct": sig.get("atr_pct", 0),
                "profit_pct": sig.get("profit_pct", 0),
                "rsi": round(sig.get("rsi", 0), 1),
                "macd_hist": round(sig.get("macd_hist", 0), 4),
                "adx": round(sig.get("adx", 0), 2),
                "vwap": round(sig.get("vwap", 0), 2),
                "vol_surge": round(sig.get("vol_surge", 1), 2),
                "reasons": sig.get("reasons", [])[:4],
                "sector_strength": sig.get("sector_strength", "Medium"),
                "expected_move_pct": sig.get(
                    "expected_move_pct", round(abs(target1 - entry) / entry * 100, 2)
                ),
                "estimated_profit": estimated_profit,
                "mentor_advice": advice,
            }
        )
        deployed += actual_cost

    return positions, deployed


def allocate(
    capital: float,
    signals: list,
    style: str = "Intraday Momentum",
    risk: str = "Medium",
    max_recommendations: int = 5,
) -> dict:
    """
    Build a high-return allocation plan targeting 10-20% on invested capital.

    Key differences from standard allocator:
    1. Score = confidence × ATR% (prefer HIGH VOLATILITY stocks)
    2. Target = 10-15% gain on position (not ATR × 2)
    3. Stop  = 4-5% loss max (wider stop for volatile stocks)
    4. Min profit target per position = 8% of amount invested
    5. Filter out stocks where max profit < 8% of invested amount
    """

    if capital <= 0:
        return {"error": "Capital must be > 0", "positions": []}
    if not signals:
        return {"error": "No signals", "positions": []}

    max_positions, deployable, risk_pct, max_per_stock, min_profit_target = _get_tier_config(
        capital, risk, max_recommendations
    )

    candidates = _filter_and_score_signals(signals, deployable, max_positions)

    if not candidates:
        return {
            "capital": round(capital, 2),
            "deployable": round(deployable, 2),
            "positions": [],
            "position_count": 0,
            "message": (
                "No high-return BUY signals found right now. "
                "The market may be closed or in a bearish/sideways phase. "
                "Best scan time: 9:30–11:00 AM IST for intraday momentum."
            ),
        }

    positions, deployed = _build_positions(
        candidates, capital, deployable, max_per_stock, risk_pct, min_profit_target
    )

    if not positions:
        return {
            "capital": round(capital, 2),
            "deployable": round(deployable, 2),
            "positions": [],
            "position_count": 0,
            "message": f"Signal prices exceed available capital of ₹{capital:,.0f}. Try during market hours when more volatile low-price stocks have signals.",
        }

    total_profit = sum(p["potential_profit"] for p in positions)
    total_loss = sum(p["potential_loss"] for p in positions)
    total_profit_pct = round((total_profit / capital) * 100, 1)
    cash_reserve = round(capital - deployed, 2)

    return {
        "capital": round(capital, 2),
        "deployable": round(deployable, 2),
        "total_deployed": round(deployed, 2),
        "cash_reserve": cash_reserve,
        "deployment_pct": round((deployed / capital) * 100, 1),
        "positions": positions,
        "position_count": len(positions),
        "total_potential_profit": round(total_profit, 2),
        "total_potential_loss": round(total_loss, 2),
        "total_profit_pct": total_profit_pct,
        "portfolio_rr": round(total_profit / total_loss, 2) if total_loss > 0 else 0,
        "max_risk_pct": round((total_loss / capital) * 100, 1),
        "message": None,
    }
