"""N8n webhook endpoints for monitoring and trigger actions."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Request
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.api.deps import DbDep
from app.db.models import PredictionsHistory
import db
from governance_worker import check_risk_limits

router = APIRouter(prefix="/api/n8n", tags=["n8n"])
agent_router = APIRouter(prefix="/api/agent", tags=["agent"])

# ----------------------------------------------------------------------
# Kill-switch check
# ----------------------------------------------------------------------
@router.get("/kill-switch-check")
async def n8n_kill_switch_check(request: Request):
    """Return kill-switch status computed from governance logic."""
    try:
        risk_info = check_risk_limits()

        daily_limit = -3.0  # default daily loss limit
        dd_limit = -5.0  # default drawdown limit

        return {
            "triggered": risk_info["triggered"],
            "reason": risk_info["reason"],
            "daily_loss_pct": round(risk_info["daily_loss_pct"], 2),
            "drawdown_pct": round(risk_info["drawdown_pct"], 2),
            "daily_limit_pct": daily_limit,
            "drawdown_limit_pct": dd_limit,
        }
    except Exception as e:
        logger.error(f"Error in /api/n8n/kill-switch-check: {e}", exc_info=True)
        return {
            "triggered": False,
            "daily_loss_pct": None,
            "drawdown_pct": None,
            "error": str(e),
        }


# ----------------------------------------------------------------------
# Data integrity check
# ----------------------------------------------------------------------
@router.get("/data-integrity-check")
async def n8n_data_integrity_check(request: Request, db_session: Session = DbDep):
    """Return data confidence score and missing-trade alert."""
    try:
        from data_validator import calculate_data_confidence

        # Reuse existing calculate_data_confidence logic.
        result = calculate_data_confidence(limit=100, persist=False)
        confidence_score = result.get("confidence_score", 100.0) if isinstance(result, dict) else 100.0

        # Count missing trades: predictions with PENDING status or null exit_price on resolved trades.
        missing_trades = 0
        try:
            pending = db_session.query(PredictionsHistory).filter(PredictionsHistory.status == "PENDING").count()
            missing_exits = db_session.query(PredictionsHistory).filter(
                PredictionsHistory.status.in_(["WIN", "LOSS", "TARGET_HIT", "STOP_HIT"]),
                PredictionsHistory.exit_price.is_(None)
            ).count()
            missing_trades = pending + missing_exits
            alert_needed = (missing_trades > 0) or (confidence_score < 80.0)
        except Exception:
            alert_needed = confidence_score < 80.0

        return {
            "confidence_score": round(confidence_score, 2),
            "missing_trades": missing_trades,
            "alert_needed": alert_needed,
        }
    except Exception as e:
        logger.error(f"Error in /api/n8n/data-integrity-check: {e}", exc_info=True)
        return {
            "confidence_score": None,
            "missing_trades": None,
            "alert_needed": True,
            "error": str(e),
        }


# ----------------------------------------------------------------------
# Metrics (resolved predictions only)
# ----------------------------------------------------------------------
@router.get("/metrics")
async def n8n_metrics(request: Request, db_session: Session = DbDep):
    """Return trading metrics computed from resolved predictions_history rows."""
    try:
        # Only resolved trades (WIN/LOSS/TARGET_HIT/STOP_HIT/MANUAL_EXIT) — exclude TIMEOUT per requirements.
        trades = (
            db_session.query(PredictionsHistory)
            .filter(PredictionsHistory.status.in_(["WIN", "LOSS", "TARGET_HIT", "STOP_HIT", "RESOLVED", "MANUAL_EXIT"]))
            .all()
        )

        total_trades = len(trades)

        if total_trades == 0:
            # No resolved trades yet — return nulls, not fabricated numbers.
            return {
                "profit_factor": None,
                "ev_pct": None,
                "win_rate": None,
                "total_trades": 0,
                "note": "No resolved trades yet; values are null.",
            }

        wins = [t for t in trades if (t.pnl_pct or 0.0) > 0 or t.actual_outcome == "TARGET_HIT" or t.status == "WIN"]
        losses = [t for t in trades if (t.pnl_pct or 0.0) < 0 or t.actual_outcome == "STOP_HIT" or t.status == "LOSS"]
        win_count = len(wins)

        # Win rate: wins / total resolved (excludes TIMEOUT).
        win_rate = win_count / total_trades

        # PnL calculations for profit factor and EV.
        win_pnl = sum(abs(t.pnl_inr or t.pnl_pct or 0.0) for t in wins)
        loss_pnl = sum(abs(t.pnl_inr or t.pnl_pct or 0.0) for t in losses)

        # Profit factor = gross wins / gross losses (null if no losses).
        profit_factor = round(win_pnl / loss_pnl, 2) if loss_pnl > 0 else (round(win_pnl, 2) if win_pnl > 0 else None)

        # Expected value per trade as percentage of avg entry price.
        total_pnl_pct = sum(t.pnl_pct or 0.0 for t in trades)
        ev_pct = total_pnl_pct / total_trades

        return {
            "profit_factor": profit_factor,
            "ev_pct": round(ev_pct, 4),
            "win_rate": round(win_rate, 4),
            "total_trades": total_trades,
        }
    except Exception as e:
        logger.error(f"Error in /api/n8n/metrics: {e}", exc_info=True)
        return {
            "profit_factor": None,
            "ev_pct": None,
            "win_rate": None,
            "total_trades": 0,
            "error": str(e),
        }


# ----------------------------------------------------------------------
# Trigger scan
# ----------------------------------------------------------------------
@router.post("/trigger-scan", tags=["agent"])
@agent_router.post("/trigger-scan", tags=["agent"])
async def n8n_trigger_scan(request: Request):
    """Run one iteration of the scan logic and return results."""
    try:
        from trading_agent import run_scan_cycle

        results = await run_scan_cycle()
        return {
            "status": "scan_completed",
            "signals_found": len(results),
            "results": results,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Error in /api/agent/trigger-scan: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
