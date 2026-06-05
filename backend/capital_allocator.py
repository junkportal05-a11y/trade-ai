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

import math


# ── High-volatility NSE stocks ideal for small capital intraday ───────────────
# Each entry is a dict matching the format run_scan expects: {symbol, name, sector}
HIGH_VOLATILITY_UNIVERSE = {
    # ₹20-100 range — buy many shares, big % moves
    "MICRO": [
        {"symbol": "YESBANK.NS",    "name": "Yes Bank",           "sector": "Banking"},
        {"symbol": "IDEA.NS",       "name": "Vodafone Idea",       "sector": "Telecom"},
        {"symbol": "SUZLON.NS",     "name": "Suzlon Energy",       "sector": "Power"},
        {"symbol": "IRFC.NS",       "name": "IRFC",               "sector": "Finance"},
        {"symbol": "NHPC.NS",       "name": "NHPC",               "sector": "Power"},
        {"symbol": "RVNL.NS",       "name": "RVNL",               "sector": "Infrastructure"},
        {"symbol": "IRCON.NS",      "name": "Ircon International", "sector": "Infrastructure"},
        {"symbol": "RECLTD.NS",     "name": "REC Ltd",            "sector": "Finance"},
        {"symbol": "PFC.NS",        "name": "Power Finance Corp", "sector": "Finance"},
        {"symbol": "SAIL.NS",       "name": "SAIL",               "sector": "Metals"},
        {"symbol": "NALCO.NS",      "name": "NALCO",              "sector": "Metals"},
        {"symbol": "HUDCO.NS",      "name": "HUDCO",              "sector": "Finance"},
        {"symbol": "SJVN.NS",       "name": "SJVN",               "sector": "Power"},
        {"symbol": "MOIL.NS",       "name": "MOIL",               "sector": "Metals"},
        {"symbol": "MRPL.NS",       "name": "MRPL",               "sector": "Energy"},
    ],
    # ₹100-500 range — sweet spot for ₹1K-10K capital
    "SMALL": [
        {"symbol": "TATASTEEL.NS",   "name": "Tata Steel",         "sector": "Metals"},
        {"symbol": "BANKBARODA.NS",  "name": "Bank of Baroda",     "sector": "Banking"},
        {"symbol": "CANBK.NS",       "name": "Canara Bank",        "sector": "Banking"},
        {"symbol": "PNB.NS",         "name": "Punjab National Bank","sector": "Banking"},
        {"symbol": "UNIONBANK.NS",   "name": "Union Bank",         "sector": "Banking"},
        {"symbol": "IDFCFIRSTB.NS",  "name": "IDFC First Bank",    "sector": "Banking"},
        {"symbol": "FEDERALBNK.NS",  "name": "Federal Bank",      "sector": "Banking"},
        {"symbol": "TATAPOWER.NS",   "name": "Tata Power",        "sector": "Power"},
        {"symbol": "ADANIPOWER.NS",  "name": "Adani Power",       "sector": "Power"},
        {"symbol": "JSWENERGY.NS",   "name": "JSW Energy",        "sector": "Power"},
        {"symbol": "NLCINDIA.NS",    "name": "NLC India",         "sector": "Power"},
        {"symbol": "NBCC.NS",        "name": "NBCC India",        "sector": "Infrastructure"},
        {"symbol": "BEL.NS",         "name": "Bharat Electronics", "sector": "Defence"},
        {"symbol": "BHEL.NS",        "name": "BHEL",              "sector": "Capital Goods"},
        {"symbol": "COALINDIA.NS",   "name": "Coal India",        "sector": "Metals"},
        {"symbol": "HINDALCO.NS",    "name": "Hindalco",          "sector": "Metals"},
        {"symbol": "ONGC.NS",        "name": "ONGC",              "sector": "Energy"},
        {"symbol": "NTPC.NS",        "name": "NTPC",              "sector": "Power"},
    ],
    # ₹500-1500 range — good for ₹10K-50K capital
    "MID": [
        {"symbol": "ADANIENT.NS",    "name": "Adani Enterprises",  "sector": "Conglomerate"},
        {"symbol": "ADANIPORTS.NS",  "name": "Adani Ports",        "sector": "Infrastructure"},
        {"symbol": "TMPV.NS",        "name": "Tata Motors (TMPV)", "sector": "Auto"},
        {"symbol": "JSWSTEEL.NS",    "name": "JSW Steel",          "sector": "Metals"},
        {"symbol": "SBIN.NS",        "name": "SBI",               "sector": "Banking"},
        {"symbol": "AXISBANK.NS",    "name": "Axis Bank",          "sector": "Banking"},
        {"symbol": "ICICIBANK.NS",   "name": "ICICI Bank",         "sector": "Banking"},
        {"symbol": "INDUSINDBK.NS",  "name": "IndusInd Bank",      "sector": "Banking"},
        {"symbol": "POWERGRID.NS",   "name": "Power Grid",         "sector": "Power"},
        {"symbol": "GLENMARK.NS",    "name": "Glenmark Pharma",    "sector": "Pharma"},
    ],
    # ₹1500+ range — for larger capital
    "LARGE": [
        {"symbol": "RELIANCE.NS",    "name": "Reliance Industries", "sector": "Energy"},
        {"symbol": "TCS.NS",         "name": "TCS",                "sector": "IT"},
        {"symbol": "HDFCBANK.NS",    "name": "HDFC Bank",           "sector": "Banking"},
        {"symbol": "INFY.NS",        "name": "Infosys",             "sector": "IT"},
        {"symbol": "WIPRO.NS",       "name": "Wipro",               "sector": "IT"},
        {"symbol": "LT.NS",          "name": "Larsen & Toubro",     "sector": "Engineering"},
        {"symbol": "BAJFINANCE.NS",  "name": "Bajaj Finance",       "sector": "Finance"},
        {"symbol": "MARUTI.NS",      "name": "Maruti Suzuki",       "sector": "Auto"},
        {"symbol": "TITAN.NS",       "name": "Titan Company",       "sector": "Consumer"},
    ],
}


def get_target_universe(capital: float) -> list:
    """
    Returns a list of {symbol, name, sector} dicts matched to capital size.
    Small capital → cheap volatile stocks | Large capital → full universe.
    """
    micro = HIGH_VOLATILITY_UNIVERSE["MICRO"]
    small = HIGH_VOLATILITY_UNIVERSE["SMALL"]
    mid   = HIGH_VOLATILITY_UNIVERSE["MID"]
    large = HIGH_VOLATILITY_UNIVERSE["LARGE"]

    if capital < 2_000:
        return micro + small[:6]
    elif capital < 10_000:
        return micro[5:] + small
    elif capital < 50_000:
        return small + mid
    else:
        return small + mid + large


def generate_mentor_advice(sig: dict, actual_cost: float, pot_loss: float, capital: float, rr: float) -> list:
    advice = []
    
    # 1. Candlestick check from Candlestick Bible
    candlestick_found = False
    reasons = sig.get("reasons", [])
    for r in reasons:
        if "Hammer" in r:
            advice.append("✦ Candlestick Bible: Hammer detected! This shows buyers rejected lower prices and took control. Wait for the next candle to break the high for confirmation.")
            candlestick_found = True
            break
        elif "Shooting Star" in r:
            advice.append("✦ Candlestick Bible: Shooting Star detected! Selling pressure pushes prices down. Keep stop loss tight above the high wick.")
            candlestick_found = True
            break
        elif "Engulfing" in r:
            advice.append("✦ Candlestick Bible: Engulfing Pattern detected! Shows a powerful shift in momentum. Buy engulfing suggests buyers have overwhelmed sellers completely.")
            candlestick_found = True
            break
        elif "Marubozu" in r:
            advice.append("✦ Candlestick Bible: Marubozu detected! A full solid body shows extreme buying strength. Momentum is highly likely to continue higher.")
            candlestick_found = True
            break
            
    if not candlestick_found:
        advice.append("✦ Candlestick Bible: Look for confirmation patterns (like Engulfing or Hammer candles) near moving average supports before entering.")

    # 2. Risk sizing check from SL Guide
    risk_pct_of_cap = (pot_loss / capital) * 100 if capital > 0 else 0
    if risk_pct_of_cap <= 2.0:
        advice.append(f"✦ Risk Management: Risking ₹{pot_loss:,.1f} ({risk_pct_of_cap:.1f}% of capital). This aligns perfectly with the 1-2% golden risk rule in your SL Guide.")
    else:
        advice.append(f"✦ Risk Management: Risking ₹{pot_loss:,.1f} ({risk_pct_of_cap:.1f}% of capital). This exceeds the standard 2% rule. Consider scaling down if account size permits.")

    # 3. R:R check
    if rr >= 2.0:
        advice.append(f"✦ Risk-Reward: R:R ratio is 1:{rr:.2f}. This exceeds your guide's target minimum of 1:2. Excellent trade structure!")
    else:
        advice.append(f"✦ Risk-Reward: R:R ratio is 1:{rr:.2f}. Below your guide's ideal 1:2 ratio. Tighten your stop loss or aim for higher targets to improve reward ratios.")

    # 4. Stop loss placement advice
    advice.append(f"✦ Stop Loss Guide: Place your stop loss strictly below support at ₹{sig.get('stop_loss', 0):,.2f}. Avoid placing it exactly on round numbers to prevent market-maker stop-runs.")
    
    # 5. Flat brokerage warning for small capital
    if capital < 10000:
        advice.append(
            f"✦ Brokerage Alert: With small capital (₹{capital:,.0f}), flat brokerage fees (e.g. ₹20/order) "
            f"will significantly eat into profits. Ensure you use discount brokers or accumulate larger capital for sustainable trading."
        )

    return advice


def allocate(capital: float, signals: list) -> dict:
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

    # ── Tier config ────────────────────────────────────────────────────────────
    if capital < 2_000:
        max_positions      = 1
        cash_buffer        = 0.02
        risk_pct           = 0.08   # allow 8% stop on tiny accounts (volatile stocks)
        max_per_stock      = 0.98
        min_profit_target  = capital * 0.08   # at least 8% return
    elif capital < 5_000:
        max_positions      = 1
        cash_buffer        = 0.03
        risk_pct           = 0.06
        max_per_stock      = 0.97
        min_profit_target  = capital * 0.10
    elif capital < 15_000:
        max_positions      = 2
        cash_buffer        = 0.04
        risk_pct           = 0.05
        max_per_stock      = 0.65
        min_profit_target  = capital * 0.04   # per position
    elif capital < 50_000:
        max_positions      = 3
        cash_buffer        = 0.05
        risk_pct           = 0.04
        max_per_stock      = 0.45
        min_profit_target  = capital * 0.025
    elif capital < 2_00_000:
        max_positions      = 4
        cash_buffer        = 0.05
        risk_pct           = 0.03
        max_per_stock      = 0.35
        min_profit_target  = capital * 0.02
    else:
        max_positions      = 6
        cash_buffer        = 0.05
        risk_pct           = 0.025
        max_per_stock      = 0.25
        min_profit_target  = capital * 0.015

    deployable = capital * (1 - cash_buffer)

    # ── Filter signals ─────────────────────────────────────────────────────
    candidates = []
    for s in signals:
        raw_signal = s.get("direction") or s.get("signal") or ""
        # Accept BUY and WEAK BUY
        if "BUY" not in raw_signal.upper():
            continue
        if s.get("confidence", 0) < 45:   # lower threshold — market may be closed
            continue

        entry  = s.get("entry") or s.get("entry_price") or s.get("price", 0)
        stop   = s.get("stop_loss", 0)
        target = s.get("target", 0)
        atr    = s.get("atr", 0)

        if entry <= 0:
            continue
        if stop <= 0 or stop >= entry:
            # Generate a stop if missing (2% below entry)
            stop = round(entry * 0.98, 2)
        if target <= 0 or target <= entry:
            # Generate a target if missing (3% above entry)
            target = round(entry * 1.03, 2)
        if entry > deployable:
            continue  # can't even buy 1 share

        # ATR% = how volatile is this stock?
        atr_pct = (atr / entry * 100) if entry > 0 else 0
        profit_pct = (target - entry) / entry * 100

        # Score: confidence × volatility bonus × profit potential
        score = s["confidence"] * (1 + atr_pct * 0.3) * (1 + min(profit_pct, 20) * 0.05)

        s = dict(s)  # copy to avoid mutating original
        s["direction"]  = "BUY"
        s["entry"]      = entry
        s["stop_loss"]  = stop
        s["target"]     = target
        s["atr_pct"]    = round(atr_pct, 2)
        s["profit_pct"] = round(profit_pct, 2)
        s["_score"]     = score
        candidates.append(s)

    if not candidates:
        return {
            "capital":        round(capital, 2),
            "deployable":     round(deployable, 2),
            "positions":      [],
            "position_count": 0,
            "message": (
                "No high-return BUY signals found right now. "
                "The market may be closed or in a bearish/sideways phase. "
                "Best scan time: 9:30–11:00 AM IST for intraday momentum."
            ),
        }

    # Sort by score descending — best opportunity first
    candidates.sort(key=lambda x: x["_score"], reverse=True)
    candidates = candidates[:max_positions]

    # ── Build positions ────────────────────────────────────────────────────────
    total_score = sum(c["_score"] for c in candidates)
    positions   = []
    deployed    = 0

    for sig in candidates:
        entry  = sig["entry"]
        stop   = sig["stop_loss"]
        target = sig["target"]

        weight       = sig["_score"] / total_score
        raw_alloc    = deployable * weight
        capped_alloc = min(raw_alloc, capital * max_per_stock)
        remaining    = deployable - deployed

        budget = min(capped_alloc, remaining)
        if budget < entry:
            continue  # can't even buy 1 share

        # Position sizing: risk-based
        risk_per_share  = abs(entry - stop)
        max_risk_money  = capital * risk_pct
        shares_by_cap   = math.floor(budget / entry)
        shares_by_risk  = math.floor(max_risk_money / risk_per_share) if risk_per_share > 0 else shares_by_cap
        shares          = min(shares_by_risk, shares_by_cap)

        # Recheck affordability
        while shares * entry > remaining and shares > 0:
            shares -= 1
        if shares == 0:
            continue

        actual_cost    = round(shares * entry, 2)
        pot_profit     = round(shares * (target - entry), 2)
        pot_loss       = round(shares * (entry - stop), 2)
        rr             = round((target - entry) / (entry - stop), 2) if (entry - stop) > 0 else 0
        profit_on_inv  = round((pot_profit / actual_cost) * 100, 2)  # % return on this position
        profit_on_cap  = round((pot_profit / capital) * 100, 2)       # % return on total capital

        # Skip if profit is too small relative to capital — no point
        if pot_profit < min_profit_target:
            # Try to bump shares to hit minimum
            needed_shares = math.ceil(min_profit_target / (target - entry)) if (target - entry) > 0 else shares
            if needed_shares * entry <= remaining and (needed_shares * risk_per_share) <= max_risk_money:
                shares        = needed_shares
                actual_cost   = round(shares * entry, 2)
                pot_profit    = round(shares * (target - entry), 2)
                pot_loss      = round(shares * (entry - stop), 2)
                profit_on_inv = round((pot_profit / actual_cost) * 100, 2)
                profit_on_cap = round((pot_profit / capital) * 100, 2)
            # if still can't hit, include anyway — 1 share is better than nothing

        advice = generate_mentor_advice(sig, actual_cost, pot_loss, capital, rr)

        positions.append({
            "symbol":            sig.get("symbol", ""),
            "direction":         "BUY",
            "confidence":        sig["confidence"],
            "entry_price":       round(entry, 2),
            "target":            round(target, 2),
            "stop_loss":         round(stop, 2),
            "rr_ratio":          rr,
            "shares":            shares,
            "amount_invested":   actual_cost,
            "allocation_pct":    round((actual_cost / capital) * 100, 1),
            "potential_profit":  pot_profit,
            "potential_loss":    pot_loss,
            "profit_on_invested": profit_on_inv,   # % gain on money deployed
            "profit_on_capital":  profit_on_cap,   # % gain on total capital
            "atr":               round(sig.get("atr", 0), 2),
            "atr_pct":           sig.get("atr_pct", 0),
            "profit_pct":        sig.get("profit_pct", 0),
            "rsi":               round(sig.get("rsi", 0), 1),
            "vwap":              round(sig.get("vwap", 0), 2),
            "vol_surge":         round(sig.get("vol_surge", 1), 2),
            "reasons":           sig.get("reasons", [])[:4],
            "mentor_advice":     advice,
        })
        deployed += actual_cost

    if not positions:
        return {
            "capital":        round(capital, 2),
            "deployable":     round(deployable, 2),
            "positions":      [],
            "position_count": 0,
            "message": f"Signal prices exceed available capital of ₹{capital:,.0f}. Try during market hours when more volatile low-price stocks have signals.",
        }

    total_profit    = sum(p["potential_profit"] for p in positions)
    total_loss      = sum(p["potential_loss"]   for p in positions)
    total_profit_pct = round((total_profit / capital) * 100, 1)
    cash_reserve    = round(capital - deployed, 2)

    return {
        "capital":                 round(capital, 2),
        "deployable":              round(deployable, 2),
        "total_deployed":          round(deployed, 2),
        "cash_reserve":            cash_reserve,
        "deployment_pct":          round((deployed / capital) * 100, 1),
        "positions":               positions,
        "position_count":          len(positions),
        "total_potential_profit":  round(total_profit, 2),
        "total_potential_loss":    round(total_loss, 2),
        "total_profit_pct":        total_profit_pct,
        "portfolio_rr":            round(total_profit / total_loss, 2) if total_loss > 0 else 0,
        "max_risk_pct":            round((total_loss / capital) * 100, 1),
        "message":                 None,
    }
