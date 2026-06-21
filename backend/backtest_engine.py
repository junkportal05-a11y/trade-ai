"""
backtest_engine.py — Dynamic Historical Strategy Backtester for APEXTRADE
========================================================================
Downloads daily data, computes quant signals, and runs a chronological trade simulation.
"""

import math
import pandas as pd
import numpy as np
from dataclasses import dataclass
from signals import download_market_data_df


@dataclass
class BacktestConfig:
    period_range: str = "6mo"
    initial_capital: float = 10000.0
    stop_atr: float = 1.5
    target_atr: float = 2.5
    entry_score: int = 5
    risk_pct: float = 0.02
    early_exit: int = -4

def resolve_candle_pessimistic(candle: dict, entry: float, target: float, stop: float, direction: str) -> tuple[str, float]:
    """
    Evaluates a candle against entry/target/stop.
    Pessimistic: If both target and stop are touched, stop takes priority.
    Returns (result, exit_price) where result is "WIN", "LOSS", or None.
    """
    high = candle.get("high")
    low = candle.get("low")
    open_p = candle.get("open", low) # Fallback if open missing
    
    if direction in ["BUY", "BULLISH"]:
        if low <= stop:
            exit_p = min(open_p, stop)
            return "LOSS", exit_p
        if high >= target:
            exit_p = max(open_p, target)
            return "WIN", exit_p
            
    elif direction in ["SELL", "BEARISH"]:
        if high >= stop:
            exit_p = max(open_p, stop)
            return "LOSS", exit_p
        if low <= target:
            exit_p = min(open_p, target)
            return "WIN", exit_p
            
    return None, None



def run_historical_backtest(
    symbol: str,
    config: BacktestConfig = None,
) -> dict:
    """
    Runs a historical strategy backtest on Daily (1D) bars with configurable risk/target and early exit thresholds.
    """
    if config is None:
        config = BacktestConfig()

    try:
        # Download daily data via unified abstraction layer
        df = download_market_data_df(symbol, config.period_range, "1d")

        if df is None or len(df) < 30:
            return {"error": f"Insufficient historical data fetched for {symbol}."}

        # Flatten multi-level columns if returned by provider
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.dropna(subset=["Close", "High", "Low", "Open", "Volume"])
        if len(df) < 30:
            return {"error": "Insufficient historical data after cleaning."}

        df = _compute_indicators(df)

        # ── Chronological Simulation Loop ─────────────────────────────────────
        capital = config.initial_capital
        position = (
            None  # None or dict: {entry_price, stop_loss, target, shares, entry_date}
        )
        trades = []
        equity_curve = []

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        open_p = df["Open"]

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
                candle = {"high": curr_high, "low": curr_low, "open": float(open_p.iloc[i])}
                result, exit_p = resolve_candle_pessimistic(
                    candle,
                    entry=position["entry_price"],
                    target=position["target"],
                    stop=position["stop_loss"],
                    direction="BUY" # Currently only BUY supported in backtest loop
                )
                
                if result == "LOSS":
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
                            "reason": "Hard stop-loss level triggered."
                            if exit_p == position["stop_loss"]
                            else f"Gap down below stop-loss. Filled at open (₹{round(exit_p, 2)}).",
                        }
                    )
                    position = None
                    continue

                elif result == "WIN":
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
                            "reason": "Take-profit target hit."
                            if exit_p == position["target"]
                            else f"Gap up above target. Filled at open (₹{round(exit_p, 2)}).",
                        }
                    )
                    position = None
                    continue

            # Calculate signals for today
            score = _calculate_daily_score(df, i)

            # Check early exits on existing position if trend turns
            if position and score <= config.early_exit:
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

            # Check Entry Condition (Score >= config.entry_score, long-only)
            if not position and score >= config.entry_score:
                if np.isnan(atr_val) or np.isnan(price):
                    continue
                # Risk Sizing Rule
                stop_loss = round(price - config.stop_atr * atr_val, 2)
                target = round(price + config.target_atr * atr_val, 2)

                if np.isnan(stop_loss) or np.isnan(target):
                    continue

                risk_per_share = price - stop_loss
                if risk_per_share <= 0:
                    continue

                max_risk_money = capital * config.risk_pct
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

        total_pnl = round(capital - config.initial_capital, 2)
        total_pnl_pct = round((total_pnl / config.initial_capital) * 100, 2)

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
            "period": config.period_range,
            "initial_capital": config.initial_capital,
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
