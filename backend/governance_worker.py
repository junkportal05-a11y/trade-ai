"""
Risk governance background loop.
Monitors daily loss limits and drawdown kill switches.
"""
import asyncio
import db
from app.core.logging import logger
from app.core.executors import governance_executor
from app.core.worker_health import beat


def check_risk_limits() -> dict:
    """
    Calculate risk metrics and check for kill switch triggers.
    Returns dict with triggered status, reason, and percentages.
    """
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
            drawdown_pct = ((current_eq - peak_eq) / peak_eq) * 100
        else:
            drawdown_pct = 0.0

        daily_limit = risk_settings.get("daily_loss_limit", -3.0)
        dd_limit = risk_settings.get("daily_drawdown_limit", -5.0)

        # Check which limit is triggered
        triggered = daily_loss_pct <= daily_limit or drawdown_pct <= dd_limit
        reason = ""
        if daily_loss_pct <= daily_limit:
            reason = f"daily_loss_pct={daily_loss_pct:.2f}% <= limit={daily_limit}%"
        elif drawdown_pct <= dd_limit:
            reason = f"drawdown_pct={drawdown_pct:.2f}% <= limit={dd_limit}%"

        return {
            "triggered": triggered,
            "reason": reason,
            "daily_loss_pct": daily_loss_pct,
            "drawdown_pct": drawdown_pct,
        }
    except Exception as e:
        logger.error(f"Error in check_risk_limits: {e}")
        return {
            "triggered": False,
            "reason": "error",
            "daily_loss_pct": 0.0,
            "drawdown_pct": 0.0,
        }


async def governance_loop():
    """
    Background task that runs every 60 seconds.
    Monitors portfolio risk limits and enforces kill switches.
    """
    while True:
        try:
            beat("governance")
            loop = asyncio.get_event_loop()
            risk_info = await loop.run_in_executor(
                governance_executor, check_risk_limits
            )

            if risk_info["triggered"]:
                logger.error(
                    f"[governance] KILL SWITCH TRIGGERED: {risk_info['reason']}"
                )
                await loop.run_in_executor(
                    governance_executor, db.set_bot_state, "PAUSED"
                )
            else:
                logger.info(
                    f"[governance] Daily loss check: {risk_info['daily_loss_pct']:.2f}% | "
                    f"Drawdown: {risk_info['drawdown_pct']:.2f}%"
                )

        except Exception as e:
            logger.error(f"[governance] error: {e}")

        await asyncio.sleep(60)