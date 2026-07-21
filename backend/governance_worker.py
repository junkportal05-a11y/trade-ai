"""
governance_worker.py
Risk governance background loop.
Monitors daily loss limits and drawdown kill switches.
"""
import asyncio
import db
from app.core.logging import logger

async def governance_loop():
    """
    Background task that runs every 60 seconds.
    Monitors portfolio risk limits and enforces kill switches.
    """
    while True:
        try:
            risk_settings = db.get_risk_settings()
            portfolio = db.get_portfolio_state()

            current_eq = portfolio.get("current_equity", 100000.0)
            daily_start = portfolio.get("daily_equity", 100000.0)
            peak_eq = portfolio.get("peak_equity", current_eq)

            if daily_start > 0:
                daily_loss_pct = ((current_eq - daily_start) / daily_start) * 100
            else:
                daily_loss_pct = 0.0

            if peak_eq > 0:
                peak_dd_pct = ((current_eq - peak_eq) / peak_eq) * 100
            else:
                peak_dd_pct = 0.0

            daily_limit = risk_settings.get("daily_loss_limit", -3.0)
            dd_limit = risk_settings.get("daily_drawdown_limit", -5.0)

            if daily_loss_pct <= daily_limit:
                logger.info(
                    f"[governance] DAILY LOSS KILL SWITCH: {daily_loss_pct:.2f}% "
                    f"(limit: {daily_limit}%)"
                )

            if peak_dd_pct <= dd_limit:
                logger.info(
                    f"[governance] DRAWDOWN KILL SWITCH: {peak_dd_pct:.2f}% "
                    f"(limit: {dd_limit}%)"
                )

        except Exception as e:
            logger.error(f"[governance] error: {e}")

        await asyncio.sleep(60)