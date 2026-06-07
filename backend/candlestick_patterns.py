import numpy as np
import pandas as pd
from typing import Optional, Tuple

# ══════════════════════════════════════════════════════════════════════════════
#  CANDLESTICK PATTERN DETECTORS
# ══════════════════════════════════════════════════════════════════════════════

def detect_doji(df: pd.DataFrame) -> Tuple[bool, bool, bool]:
    """
    Detects Doji, Dragonfly Doji, and Gravestone Doji on the latest candle.
    Returns (is_doji, is_dragonfly, is_gravestone).
    """
    if len(df) < 1:
        return False, False, False

    o = float(df["Open"].iloc[-1])
    h = float(df["High"].iloc[-1])
    l = float(df["Low"].iloc[-1])
    c = float(df["Close"].iloc[-1])

    rng = (h - l) if (h - l) > 0 else 0.001
    body = abs(c - o)
    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l

    is_standard = body <= 0.1 * rng
    is_dragonfly = is_standard and (upper_wick <= 0.1 * rng) and (lower_wick >= 0.7 * rng)
    is_gravestone = is_standard and (lower_wick <= 0.1 * rng) and (upper_wick >= 0.7 * rng)

    # Standard Doji is True if it's doji but not dragonfly/gravestone
    is_standard = is_standard and not (is_dragonfly or is_gravestone)

    return is_standard, is_dragonfly, is_gravestone


def detect_hammer_shooting_star(df: pd.DataFrame) -> Tuple[bool, bool]:
    """
    Detects Hammer (bullish) and Shooting Star (bearish) on the latest candle.
    Returns (is_hammer, is_shooting_star).
    """
    if len(df) < 1:
        return False, False

    o = float(df["Open"].iloc[-1])
    h = float(df["High"].iloc[-1])
    l = float(df["Low"].iloc[-1])
    c = float(df["Close"].iloc[-1])

    rng = (h - l) if (h - l) > 0 else 0.001
    body = abs(c - o)
    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l

    # Hammer: long lower shadow, small body near high, tiny upper shadow
    is_hammer = (lower_wick >= 2 * body) and (upper_wick <= 0.1 * rng) and (body >= 0.05 * rng)
    # Shooting Star: long upper shadow, small body near low, tiny lower shadow
    is_shooting_star = (upper_wick >= 2 * body) and (lower_wick <= 0.1 * rng) and (body >= 0.05 * rng)

    return is_hammer, is_shooting_star


def detect_engulfing(df: pd.DataFrame) -> Tuple[bool, bool]:
    """
    Detects Bullish and Bearish Engulfing on the latest candle.
    Returns (is_bullish_engulfing, is_bearish_engulfing).
    """
    if len(df) < 2:
        return False, False

    o1, c1 = float(df["Open"].iloc[-2]), float(df["Close"].iloc[-2])
    o2, c2 = float(df["Open"].iloc[-1]), float(df["Close"].iloc[-1])

    is_c1_bearish = c1 < o1
    is_c1_bullish = c1 > o1
    is_c2_bullish = c2 > o2
    is_c2_bearish = c2 < o2

    # Bullish Engulfing: bearish candle engulfed by a larger bullish candle
    bullish = is_c1_bearish and is_c2_bullish and (c2 >= o1) and (o2 <= c1)
    # Bearish Engulfing: bullish candle engulfed by a larger bearish candle
    bearish = is_c1_bullish and is_c2_bearish and (c2 <= o1) and (o2 >= c1)

    return bullish, bearish


def detect_harami(df: pd.DataFrame) -> Tuple[bool, bool]:
    """
    Detects Bullish and Bearish Harami on the latest candle.
    Returns (is_bullish_harami, is_bearish_harami).
    """
    if len(df) < 2:
        return False, False

    o1, c1 = float(df["Open"].iloc[-2]), float(df["Close"].iloc[-2])
    o2, c2 = float(df["Open"].iloc[-1]), float(df["Close"].iloc[-1])

    # Bullish Harami: Large bearish body, small body contained inside it
    bullish = (c1 < o1) and (max(o2, c2) <= o1) and (min(o2, c2) >= c1) and (abs(c2 - o2) < abs(c1 - o1) * 0.5)
    # Bearish Harami: Large bullish body, small body contained inside it
    bearish = (c1 > o1) and (max(o2, c2) <= c1) and (min(o2, c2) >= o1) and (abs(c2 - o2) < abs(c1 - o1) * 0.5)

    return bullish, bearish


def detect_stars(df: pd.DataFrame) -> Tuple[bool, bool]:
    """
    Detects Morning Star (bullish reversal) and Evening Star (bearish reversal).
    Returns (is_morning_star, is_evening_star).
    """
    if len(df) < 3:
        return False, False

    o1, c1 = float(df["Open"].iloc[-3]), float(df["Close"].iloc[-3])
    o2, c2 = float(df["Open"].iloc[-2]), float(df["Close"].iloc[-2])
    o3, c3 = float(df["Open"].iloc[-1]), float(df["Close"].iloc[-1])

    body1 = abs(c1 - o1)
    body2 = abs(c2 - o2)

    # Morning Star: Bearish candle -> Small star -> Bullish candle closing > 50% body1
    morning = (c1 < o1) and (body2 <= 0.3 * body1) and (c3 > o3) and (c3 >= o1 - 0.5 * body1)
    # Evening Star: Bullish candle -> Small star -> Bearish candle closing < 50% body1
    evening = (c1 > o1) and (body2 <= 0.3 * body1) and (c3 < o3) and (c3 <= o1 + 0.5 * body1)

    return morning, evening


def detect_tweezers(df: pd.DataFrame) -> Tuple[bool, bool]:
    """
    Detects Tweezer Bottom (bullish) and Tweezer Top (bearish) on the latest candles.
    Returns (is_tweezer_bottom, is_tweezer_top).
    """
    if len(df) < 2:
        return False, False

    h1, l1 = float(df["High"].iloc[-2]), float(df["Low"].iloc[-2])
    h2, l2 = float(df["High"].iloc[-1]), float(df["Low"].iloc[-1])
    c2 = float(df["Close"].iloc[-1])

    # Threshold for matching: 0.05% of close price
    threshold = 0.0005 * c2

    # Tweezer Bottom: Matching lows
    bottom = abs(l1 - l2) <= threshold and (min(df["Open"].iloc[-2], df["Close"].iloc[-2]) - l1 > 0.1 * (h1 - l1))
    # Tweezer Top: Matching highs
    top = abs(h1 - h2) <= threshold and (h1 - max(df["Open"].iloc[-2], df["Close"].iloc[-2]) > 0.1 * (h1 - l1))

    return bottom, top


# ══════════════════════════════════════════════════════════════════════════════
#  PIN BAR STRATEGIES (WITH TREND, COUNTER-TREND, CONFLUENCE)
# ══════════════════════════════════════════════════════════════════════════════

def detect_pin_bars(df: pd.DataFrame, ema21_val: float, rsi_val: float, support_level: Optional[float] = None, resistance_level: Optional[float] = None) -> Tuple[str, list[str]]:
    """
    Detects Pin Bars and evaluates their strategy categories.
    Returns (pin_bar_type: "BULLISH", "BEARISH", or "NONE", list_of_confluences).
    """
    is_hammer, is_shooting_star = detect_hammer_shooting_star(df)
    _, is_dragonfly, is_gravestone = detect_doji(df)

    is_bullish_pin = is_hammer or is_dragonfly
    is_bearish_pin = is_shooting_star or is_gravestone

    confluences = []
    
    if is_bullish_pin:
        l = float(df["Low"].iloc[-1])
        c = float(df["Close"].iloc[-1])
        
        # Confluence 1: Near Support
        if support_level and abs(l - support_level) <= 0.008 * c:
            confluences.append("Support Level Confluence")
        
        # Confluence 2: Touching/near EMA21
        if ema21_val and abs(l - ema21_val) <= 0.005 * c:
            confluences.append("EMA21 Confluence")
            
        # Confluence 3: Counter-Trend extreme oversold
        if rsi_val < 30:
            confluences.append("Oversold Reversal (RSI < 30)")
        # Confluence 4: With Trend
        elif ema21_val and c > ema21_val:
            confluences.append("With-Trend Continuation")

        return "BULLISH", confluences

    elif is_bearish_pin:
        h = float(df["High"].iloc[-1])
        c = float(df["Close"].iloc[-1])
        
        # Confluence 1: Near Resistance
        if resistance_level and abs(h - resistance_level) <= 0.008 * c:
            confluences.append("Resistance Level Confluence")
        
        # Confluence 2: Touching/near EMA21
        if ema21_val and abs(h - ema21_val) <= 0.005 * c:
            confluences.append("EMA21 Confluence")
            
        # Confluence 3: Counter-Trend extreme overbought
        if rsi_val > 70:
            confluences.append("Overbought Reversal (RSI > 70)")
        # Confluence 4: With Trend
        elif ema21_val and c < ema21_val:
            confluences.append("With-Trend Continuation")

        return "BEARISH", confluences

    return "NONE", []


# ══════════════════════════════════════════════════════════════════════════════
#  INSIDE BARS & FALSE BREAKOUT (HIKKAKE/FAKEOUT)
# ══════════════════════════════════════════════════════════════════════════════

def detect_inside_bars(df: pd.DataFrame) -> bool:
    """
    Detects if the latest candle is an Inside Bar relative to the previous candle.
    """
    if len(df) < 2:
        return False

    h1, l1 = float(df["High"].iloc[-2]), float(df["Low"].iloc[-2])
    h2, l2 = float(df["High"].iloc[-1]), float(df["Low"].iloc[-1])

    return h2 < h1 and l2 > l1


def detect_inside_bar_fakeout(df: pd.DataFrame) -> Tuple[str, float]:
    """
    Detects Hikkake / Inside Bar False Breakouts.
    Returns (fakeout_direction: "BULLISH", "BEARISH", or "NONE", trigger_price).
    """
    if len(df) < 3:
        return "NONE", 0.0

    # Candle -3: Mother Bar
    h3, l3 = float(df["High"].iloc[-3]), float(df["Low"].iloc[-3])
    # Candle -2: Inside Bar
    h2, l2 = float(df["High"].iloc[-2]), float(df["Low"].iloc[-2])
    # Candle -1: Latest Candle (Breakout attempt and reversal)
    h1, l1 = float(df["High"].iloc[-1]), float(df["Low"].iloc[-1])
    c1, o1 = float(df["Close"].iloc[-1]), float(df["Open"].iloc[-1])

    is_inside = h2 < h3 and l2 > l3
    if not is_inside:
        return "NONE", 0.0

    # Bullish Fakeout: Inside bar low is breached, but it closes above the Inside Bar high
    # (Triggers shorts, traps them, and breaks bullishly)
    if l1 < l2 and c1 > h2:
        return "BULLISH", h2

    # Bearish Fakeout: Inside bar high is breached, but it closes below the Inside Bar low
    # (Triggers longs, traps them, and breaks bearishly)
    if h1 > h2 and c1 < l2:
        return "BEARISH", l2

    return "NONE", 0.0


# ══════════════════════════════════════════════════════════════════════════════
#  SMART MONEY CONCEPTS (BOS, CHOCH, SWINGS)
# ══════════════════════════════════════════════════════════════════════════════

def detect_swings(df: pd.DataFrame, window: int = 5) -> Tuple[list[Tuple[int, float]], list[Tuple[int, float]]]:
    """
    Detects Swing Highs and Swing Lows from the past N candles.
    Returns (list_of_swing_highs, list_of_swing_lows) as [(index, price), ...]
    """
    highs = df["High"].values
    lows = df["Low"].values
    
    swing_highs = []
    swing_lows = []
    
    for i in range(window, len(df) - window):
        # Check swing high
        val_h = highs[i]
        if val_h == max(highs[i - window : i + window + 1]):
            # Verify it's unique in the window to avoid duplicates
            if all(val_h > highs[j] for j in range(i - window, i)) and all(val_h >= highs[j] for j in range(i + 1, i + window + 1)):
                swing_highs.append((i, float(val_h)))
                
        # Check swing low
        val_l = lows[i]
        if val_l == min(lows[i - window : i + window + 1]):
            if all(val_l < lows[j] for j in range(i - window, i)) and all(val_l <= lows[j] for j in range(i + 1, i + window + 1)):
                swing_lows.append((i, float(val_l)))
                
    return swing_highs, swing_lows


def detect_structure_breaks(df: pd.DataFrame, swing_highs: list, swing_lows: list) -> Tuple[str, str]:
    """
    Checks for Break of Structure (BOS) or Change of Character (CHoCH) on the latest candle.
    Returns (break_type: "BULLISH", "BEARISH", or "NONE", reason: str)
    """
    if len(df) < 5 or not swing_highs or not swing_lows:
        return "NONE", ""

    c1 = float(df["Close"].iloc[-1])
    h1 = float(df["High"].iloc[-1])
    l1 = float(df["Low"].iloc[-1])
    
    # Sort swing levels by time (index)
    sorted_highs = sorted(swing_highs, key=lambda x: x[0])
    sorted_lows = sorted(swing_lows, key=lambda x: x[0])
    
    last_high_idx, last_high_val = sorted_highs[-1]
    last_low_idx, last_low_val = sorted_lows[-1]
    
    # Check for Bullish break
    if c1 > last_high_val:
        # Determine if it's BOS (with trend) or CHoCH (reversal)
        # If previous swing high was a Lower High (indicating prior downtrend), breaking it is CHoCH.
        if len(sorted_highs) >= 2:
            prev_high_val = sorted_highs[-2][1]
            if last_high_val < prev_high_val:
                return "BULLISH", f"CHoCH (Bullish Reversal above LH {last_high_val:.2f})"
        return "BULLISH", f"BOS (Bullish Continuation above HH {last_high_val:.2f})"

    # Check for Bearish break
    if c1 < last_low_val:
        # If previous swing low was a Higher Low (indicating prior uptrend), breaking it is CHoCH.
        if len(sorted_lows) >= 2:
            prev_low_val = sorted_lows[-2][1]
            if last_low_val > prev_low_val:
                return "BEARISH", f"CHoCH (Bearish Reversal below HL {last_low_val:.2f})"
        return "BEARISH", f"BOS (Bearish Continuation below LL {last_low_val:.2f})"
        
    return "NONE", ""


def find_support_resistance(df: pd.DataFrame, swing_highs: list, swing_lows: list) -> Tuple[Optional[float], Optional[float]]:
    """
    Groups recent swing points to find nearest Support (below price) and Resistance (above price).
    Returns (nearest_support, nearest_resistance).
    """
    if not swing_highs or not swing_lows:
        return None, None

    c1 = float(df["Close"].iloc[-1])
    
    # Extract prices
    high_prices = [h[1] for h in swing_highs[-10:]] # last 10 swings
    low_prices = [l[1] for l in swing_lows[-10:]]
    
    # Nearest support is the highest swing low that is below current price
    supports = [val for val in low_prices if val < c1]
    support = max(supports) if supports else None
    
    # Nearest resistance is the lowest swing high that is above current price
    resistances = [val for val in high_prices if val > c1]
    resistance = min(resistances) if resistances else None
    
    return support, resistance


# ══════════════════════════════════════════════════════════════════════════════
#  RISK & POSITION SIZING CALCULATOR
# ══════════════════════════════════════════════════════════════════════════════

def calculate_risk_parameters(
    price: float, 
    signal_type: str, 
    df: pd.DataFrame, 
    support: Optional[float], 
    resistance: Optional[float], 
    capital: float, 
    risk_pct: float = 0.01
) -> Tuple[float, float, int, float]:
    """
    Calculates Stop Loss, Target, Position Size, and Risk/Reward Ratio.
    Returns (stop_loss, target, position_size, risk_reward_ratio).
    """
    # 1. Stop Loss Placement
    if signal_type == "BULLISH":
        # Stop loss below support or latest low (whichever is lower, padded by 0.2% of price)
        sl_base = support if support else float(df["Low"].iloc[-3:].min())
        stop_loss = min(sl_base, price * 0.99) - (price * 0.002)
        
        # Ensure we don't have infinite risk
        risk_per_share = price - stop_loss
        if risk_per_share <= 0:
            risk_per_share = price * 0.015
            stop_loss = price - risk_per_share
            
        # Target with 1:2 Risk-Reward Ratio
        target = price + (2.0 * risk_per_share)
        
    else: # BEARISH
        # Stop loss above resistance or latest high (whichever is higher, padded by 0.2%)
        sl_base = resistance if resistance else float(df["High"].iloc[-3:].max())
        stop_loss = max(sl_base, price * 1.01) + (price * 0.002)
        
        risk_per_share = stop_loss - price
        if risk_per_share <= 0:
            risk_per_share = price * 0.015
            stop_loss = price + risk_per_share
            
        target = price - (2.0 * risk_per_share)

    # 2. Position Sizing
    # Max loss = capital * risk_pct (e.g. 1% of ₹10,000 = ₹100)
    max_loss = capital * risk_pct
    position_size = int(max_loss // risk_per_share)
    
    # Cap position size by buying power (capital / price)
    max_buy_power = int(capital // price)
    position_size = max(1, min(position_size, max_buy_power))
    
    risk_reward_ratio = 2.0  # Strict 1:2 R:R

    return round(stop_loss, 2), round(target, 2), position_size, risk_reward_ratio
