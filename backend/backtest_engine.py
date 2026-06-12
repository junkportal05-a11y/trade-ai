"""
backtest_engine.py — Dynamic Historical Strategy Backtester for APEXTRADE
========================================================================
Downloads daily data, computes quant signals, and runs a chronological trade simulation.
"""

import math
import pandas as pd
import numpy as np
from signals import download_market_data_df


def run_historical_backtest(
    symbol: str,
    period_range: str = "6mo",
    initial_capital: float = 10000.0,
    stop_atr: float = 1.5,
    target_atr: float = 2.5,
    entry_score: int = 5,
    risk_pct: float = 0.02,
    early_exit: int = -4,
) -> dict:
    """
    Runs a historical strategy backtest on Daily (1D) bars with configurable risk/target and early exit thresholds.
    """
    try:
        # Download daily data via unified abstraction layer
        df = download_market_data_df(symbol, period_range, "1d")

        if df is None or len(df) < 30:
            return {"error": f"Insufficient historical data fetched for {symbol}."}

        # Flatten multi-level columns if returned by provider
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.dropna(subset=["Close", "High", "Low", "Open", "Volume"])
        if len(df) < 30:
            return {"error": "Insufficient historical data after cleaning."}

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        open_p = df["Open"]
        volume = df["Volume"]

        # Calculate standard indicator columns
        df["EMA_9"] = close.ewm(span=9, adjust=False).mean()
        df["EMA_21"] = close.ewm(span=21, adjust=False).mean()
        df["EMA_50"] = close.ewm(span=50, adjust=False).mean()  # Daily trend filter

        # RSI(14)
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        df["RSI_14"] = 100 - (100 / (1 + rs))

        # MACD(12,26,9)
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        df["MACD"] = ema12 - ema26
        df["MACDs"] = df["MACD"].ewm(span=9, adjust=False).mean()
        df["MACDh"] = df["MACD"] - df["MACDs"]

        # Bollinger Bands(20,2)
        bb_mid = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        df["BBU"] = bb_mid + 2 * bb_std
        df["BBL"] = bb_mid - 2 * bb_std

        # ATR(14)
        tr = pd.concat(
            [
                high - low,
                (high - close.shift()).abs(),
                (low - close.shift()).abs(),
            ],
            axis=1,
        ).max(axis=1)
        df["ATR"] = tr.rolling(14).mean()

        # Supertrend(7, 3.0)
        atr7 = tr.rolling(7).mean()
        basic_upper = (high + low) / 2 + 3.0 * atr7
        basic_lower = (high + low) / 2 - 3.0 * atr7
        supert = pd.Series(np.nan, index=df.index)
        supert_dir = pd.Series(1.0, index=df.index)

        for i in range(1, len(df)):
            bu = basic_upper.iloc[i]
            bl = basic_lower.iloc[i]
            prev_supert = supert.iloc[i - 1] if not np.isnan(supert.iloc[i - 1]) else bl
            prev_dir = supert_dir.iloc[i - 1]
            if prev_dir == 1:
                bl = max(bl, prev_supert)
            else:
                bu = min(bu, prev_supert)
            if close.iloc[i - 1] <= prev_supert:
                supert.iloc[i] = bu
                supert_dir.iloc[i] = -1
            else:
                supert.iloc[i] = bl
                supert_dir.iloc[i] = 1
        df["SUPERT"] = supert
        df["SUPERT_DIR"] = supert_dir

        # ADX(14)
        up_move = high.diff()
        down_move = -low.diff()
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
        plus_di = (
            100
            * pd.Series(plus_dm, index=df.index).rolling(14).mean()
            / df["ATR"].replace(0, np.nan)
        )
        minus_di = (
            100
            * pd.Series(minus_dm, index=df.index).rolling(14).mean()
            / df["ATR"].replace(0, np.nan)
        )
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
        df["ADX"] = dx.rolling(14).mean()

        # Stochastic(14,3,3)
        low14 = low.rolling(14).min()
        high14 = high.rolling(14).max()
        df["STOCH_K"] = 100 * (close - low14) / (high14 - low14).replace(0, np.nan)
        df["STOCH_D"] = df["STOCH_K"].rolling(3).mean()

        # Volume 20 SMA for volume anomalies
        df["VOL_SMA"] = volume.rolling(20).mean()

        # ── Chronological Simulation Loop ─────────────────────────────────────
        capital = initial_capital
        position = (
            None  # None or dict: {entry_price, stop_loss, target, shares, entry_date}
        )
        trades = []
        equity_curve = []

        # Start from bar 25 to allow indicators to warm up
        for i in range(25, len(df)):
            current_date = df.index[i].strftime("%Y-%m-%d")
            price = float(close.iloc[i])
            curr_high = float(high.iloc[i])
            curr_low = float(low.iloc[i])

            # Record daily equity (value of cash + open positions)
            pos_value = 0
            if position:
                pos_value = position["shares"] * price
            equity_curve.append(
                {"date": current_date, "value": round(capital + pos_value, 2)}
            )

            # Check open positions for Exits
            if position:
                # 1. Check Stop Loss
                if curr_low <= position["stop_loss"]:
                    # Handle gap down: if open price is below stop-loss, we get stopped out at the open price
                    exit_p = min(float(open_p.iloc[i]), position["stop_loss"])
                    pnl = (exit_p - position["entry_price"]) * position["shares"]
                    capital += position["shares"] * exit_p
                    trades.append(
                        {
                            "symbol": symbol,
                            "direction": "BUY",
                            "entry_date": position["entry_date"],
                            "exit_date": current_date,
                            "entry_price": position["entry_price"],
                            "exit_price": round(exit_p, 2),
                            "shares": position["shares"],
                            "pnl": round(pnl, 2),
                            "pnl_pct": round(
                                (pnl / (position["entry_price"] * position["shares"]))
                                * 100,
                                2,
                            ),
                            "status": "HIT_STOP",
                            "reason": "Hard stop-loss level triggered." if exit_p == position["stop_loss"] else f"Gap down below stop-loss. Filled at open (₹{round(exit_p, 2)}).",
                        }
                    )
                    position = None
                    continue

                # 2. Check Profit Target
                elif curr_high >= position["target"]:
                    # Handle gap up: if open price is above target, we get filled at the open price
                    exit_p = max(float(open_p.iloc[i]), position["target"])
                    pnl = (exit_p - position["entry_price"]) * position["shares"]
                    capital += position["shares"] * exit_p
                    trades.append(
                        {
                            "symbol": symbol,
                            "direction": "BUY",
                            "entry_date": position["entry_date"],
                            "exit_date": current_date,
                            "entry_price": position["entry_price"],
                            "exit_price": round(exit_p, 2),
                            "shares": position["shares"],
                            "pnl": round(pnl, 2),
                            "pnl_pct": round(
                                (pnl / (position["entry_price"] * position["shares"]))
                                * 100,
                                2,
                            ),
                            "status": "HIT_TARGET",
                            "reason": "Take-profit target hit." if exit_p == position["target"] else f"Gap up above target. Filled at open (₹{round(exit_p, 2)}).",
                        }
                    )
                    position = None
                    continue

            # Calculate signals for today
            score = 0
            # Indicator values
            rsi_val = float(df["RSI_14"].iloc[i])
            macd_h = float(df["MACDh"].iloc[i])
            macd_h_prev = float(df["MACDh"].iloc[i - 1])
            macd_v = float(df["MACD"].iloc[i])
            macd_s = float(df["MACDs"].iloc[i])
            ema9_v = float(df["EMA_9"].iloc[i])
            ema21_v = float(df["EMA_21"].iloc[i])
            ema50_v = float(df["EMA_50"].iloc[i])
            bbu_v = float(df["BBU"].iloc[i])
            bbl_v = float(df["BBL"].iloc[i])
            atr_val = float(df["ATR"].iloc[i])
            supert_dir = int(df["SUPERT_DIR"].iloc[i])
            adx_val = float(df["ADX"].iloc[i])
            stoch_k = float(df["STOCH_K"].iloc[i])
            stoch_d = float(df["STOCH_D"].iloc[i])
            vol_sma = float(df["VOL_SMA"].iloc[i])
            vol_val = float(volume.iloc[i])
            vol_ratio = vol_val / vol_sma if vol_sma > 0 else 1.0

            # 1. EMA 50 trend filter
            if price > ema50_v:
                score += 2
            else:
                score -= 2

            # 2. RSI Overbought/Oversold
            if 45 <= rsi_val <= 65:
                score += 1
            elif rsi_val > 70:
                score -= 2
            elif rsi_val < 35:
                score += 2

            # 3. MACD
            if macd_h > 0 and macd_h > macd_h_prev:
                score += 2
            elif macd_h < 0 and macd_h < macd_h_prev:
                score -= 2
            if macd_v > macd_s and df["MACD"].iloc[i - 1] <= df["MACDs"].iloc[i - 1]:
                score += 2

            # 4. EMA 9/21 Trend Crossover
            if ema9_v > ema21_v:
                score += 1
            else:
                score -= 1

            # 5. Bollinger Bands
            pct_b = (price - bbl_v) / (bbu_v - bbl_v) if (bbu_v - bbl_v) > 0 else 0.5
            if pct_b > 0.85:
                score -= 1
            elif pct_b < 0.15:
                score += 1

            # 6. Supertrend
            if supert_dir == 1:
                score += 2
            else:
                score -= 2

            # 7. ADX Choppiness
            if adx_val > 40:
                score += 2 if score > 0 else -2
            elif adx_val > 25:
                score += 1 if score > 0 else -1
            elif adx_val < 15:
                score = 0  # Skip completely
            elif adx_val < 20:
                score = int(score * 0.7)

            # 8. Candlestick patterns with VOLUME ANOMALY confirmation (1.3x volume requirement)
            try:
                c_open = float(open_p.iloc[i])
                c_high = float(high.iloc[i])
                c_low = float(low.iloc[i])
                c_close = float(close.iloc[i])
                p_open = float(open_p.iloc[i - 1])
                p_close = float(close.iloc[i - 1])

                c_body = abs(c_close - c_open)
                c_range = (c_high - c_low) if (c_high - c_low) > 0 else 0.001
                u_wick = c_high - max(c_open, c_close)
                l_wick = min(c_open, c_close) - c_low

                # Check if volume is anomalous (substantial trade conviction)
                has_vol_anomaly = vol_ratio >= 1.3

                if has_vol_anomaly:
                    # Hammer
                    if (
                        l_wick > (2 * c_body)
                        and u_wick < (0.1 * c_range)
                        and c_body > (0.05 * c_range)
                    ):
                        score += 3
                    # Shooting Star
                    elif (
                        u_wick > (2 * c_body)
                        and l_wick < (0.1 * c_range)
                        and c_body > (0.05 * c_range)
                    ):
                        score -= 3
                    # Engulfing
                    elif (
                        c_close > c_open
                        and p_close < p_open
                        and c_close >= p_open
                        and c_open <= p_close
                    ):
                        score += 3
                    elif (
                        c_close < c_open
                        and p_close > p_open
                        and c_close <= p_open
                        and c_open >= p_close
                    ):
                        score -= 3
            except Exception:
                pass

            # 9. Volume surger
            if vol_ratio >= 1.5:
                score += 1 if score > 0 else -1

            # Check early exits on existing position if trend turns
            if position and score <= early_exit:
                # Early exit
                pnl = (price - position["entry_price"]) * position["shares"]
                capital += position["shares"] * price
                trades.append(
                    {
                        "symbol": symbol,
                        "direction": "BUY",
                        "entry_date": position["entry_date"],
                        "exit_date": current_date,
                        "entry_price": position["entry_price"],
                        "exit_price": price,
                        "shares": position["shares"],
                        "pnl": round(pnl, 2),
                        "pnl_pct": round(
                            (pnl / (position["entry_price"] * position["shares"]))
                            * 100,
                            2,
                        ),
                        "status": "CLOSED",
                        "reason": "Early exit on bearish indicators crossover.",
                    }
                )
                position = None
                continue

            # Check Entry Condition (Score >= entry_score, long-only)
            if not position and score >= entry_score:
                if np.isnan(atr_val) or np.isnan(price):
                    continue
                # Risk Sizing Rule
                stop_loss = round(price - stop_atr * atr_val, 2)
                target = round(price + target_atr * atr_val, 2)

                if np.isnan(stop_loss) or np.isnan(target):
                    continue

                risk_per_share = price - stop_loss
                if risk_per_share <= 0:
                    continue

                max_risk_money = capital * risk_pct
                shares_by_risk = math.floor(max_risk_money / risk_per_share)
                shares_by_cap = math.floor((capital * 0.95) / price)
                shares = min(shares_by_risk, shares_by_cap)

                if shares >= 1:
                    actual_cost = round(shares * price, 2)
                    capital -= actual_cost
                    position = {
                        "entry_price": price,
                        "stop_loss": stop_loss,
                        "target": target,
                        "shares": shares,
                        "entry_date": current_date,
                    }

        # Handle any left-over active position at end of backtest range
        if position:
            last_price = float(close.iloc[-1])
            pnl = (last_price - position["entry_price"]) * position["shares"]
            capital += position["shares"] * last_price
            trades.append(
                {
                    "symbol": symbol,
                    "direction": "BUY",
                    "entry_date": position["entry_date"],
                    "exit_date": df.index[-1].strftime("%Y-%m-%d"),
                    "entry_price": position["entry_price"],
                    "exit_price": last_price,
                    "shares": position["shares"],
                    "pnl": round(pnl, 2),
                    "pnl_pct": round(
                        (pnl / (position["entry_price"] * position["shares"])) * 100, 2
                    ),
                    "status": "PENDING",
                    "reason": "Position active (unresolved at end of simulation timeframe).",
                }
            )

        # Calculate final stats
        total_trades = len(trades)
        wins = len([t for t in trades if t["pnl"] > 0])
        losses = len([t for t in trades if t["pnl"] < 0])
        win_rate = round((wins / total_trades) * 100, 1) if total_trades > 0 else 0.0

        total_pnl = round(capital - initial_capital, 2)
        total_pnl_pct = round((total_pnl / initial_capital) * 100, 2)

        # Profit factor
        gross_profit = sum(t["pnl"] for t in trades if t["pnl"] > 0)
        gross_loss = abs(sum(t["pnl"] for t in trades if t["pnl"] < 0))
        profit_factor = (
            round(gross_profit / gross_loss, 2)
            if gross_loss > 0
            else (round(gross_profit, 2) if gross_profit > 0 else 1.00)
        )

        # Calculate Max Drawdown %
        equity_series = [eq["value"] for eq in equity_curve]
        max_drawdown = 0.0
        if equity_series:
            peak = equity_series[0]
            for val in equity_series:
                if val > peak:
                    peak = val
                dd = (peak - val) / peak * 100
                if dd > max_drawdown:
                    max_drawdown = dd
        max_drawdown = round(max_drawdown, 2)

        return {
            "symbol": symbol,
            "period": period_range,
            "initial_capital": initial_capital,
            "final_capital": round(capital, 2),
            "total_pnl": total_pnl,
            "total_pnl_pct": total_pnl_pct,
            "total_trades": total_trades,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "max_drawdown": max_drawdown,
            "trades": trades,
            "equity_curve": equity_curve,
        }

    except Exception as e:
        return {"error": f"Backtest exception: {str(e)}"}
