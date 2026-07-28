"""Predictions router."""
from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import not_
from sqlalchemy.orm import Session

from app.api.deps import DbDep, SessionDep
from app.models.schemas import PredictionCreate, PredictionResolveRequest
from app.db.repositories import repo
from app.db.models import PredictionsHistory

router = APIRouter(prefix="/api", tags=["predictions"])


@router.get("/predictions", response_model=list[dict])
def get_predictions(db: Session = DbDep, _=SessionDep) -> list[dict]:
    return repo.predictions.get_all(db)


@router.get("/predictions/pending", response_model=list[dict])
def get_pending_predictions(db: Session = DbDep, _=SessionDep) -> list[dict]:
    return repo.predictions.get_pending(db)


@router.post("/predictions", response_model=dict)
def create_prediction(
    pred: PredictionCreate,
    db: Session = DbDep,
    _=SessionDep,
) -> dict:
    pred_id = repo.predictions.add(db, pred.model_dump())
    return {"id": pred_id, "status": "created"}


@router.get("/predictions/stats", response_model=dict)
def get_prediction_stats(db: Session = DbDep, _=SessionDep) -> dict:
    all_preds = db.query(PredictionsHistory).all()
    total_count = len(all_preds)
    
    resolved = [p for p in all_preds if p.status != "PENDING" and p.resolved_at is not None]
    n = len(resolved)
    
    if n == 0:
        return {
            "total_predictions": total_count,
            "resolved_predictions": 0,
            "win_rate": 0.0,
            "avg_error": 0.0,
            "profit_factor": 0.0,
            "empirical_rr_ratio": 0.0,
            "expected_value_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "best_sector": "N/A",
            "worst_sector": "N/A",
            "avg_confidence": 0.0,
            "recent_outcomes": [],
            "leaderboard": [],
        }

    wins = [r for r in resolved if (r.pnl_pct or 0) > 0]
    losses = [r for r in resolved if (r.pnl_pct or 0) < 0]
    
    gross_profit = sum(r.pnl_pct for r in wins)
    gross_loss = abs(sum(r.pnl_pct for r in losses))
    
    win_rate = round((len(wins) / n) * 100, 1)
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (round(gross_profit, 2) if gross_profit > 0 else 1.0)
    
    avg_win = (gross_profit / len(wins)) if wins else 0.0
    avg_loss = (gross_loss / len(losses)) if losses else 0.0
    empirical_rr = round(avg_win / avg_loss, 2) if avg_loss > 0 else 1.5
    
    win_prob = len(wins) / n
    ev_pct = round((win_prob * avg_win) - ((1.0 - win_prob) * avg_loss), 2)
    
    conf_scores = [r.confidence_score for r in all_preds if r.confidence_score is not None]
    avg_conf = round(sum(conf_scores) / len(conf_scores), 1) if conf_scores else 80.0

    recent = [
        {
            "id": r.id,
            "symbol": r.symbol,
            "outcome": r.actual_outcome or r.status,
            "pnl_pct": r.pnl_pct or 0.0,
            "resolved_at": r.resolved_at,
        }
        for r in resolved[-10:]
    ]

    # Dynamic: max_drawdown_pct from resolved trades equity curve
    equity = 0.0
    peak_equity = 0.0
    max_dd = 0.0
    for r in resolved:
        equity += (r.pnl_pct or 0.0)
        if equity > peak_equity:
            peak_equity = equity
        dd = ((peak_equity - equity) / peak_equity * 100) if peak_equity > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
    max_drawdown_pct = round(max_dd, 2) if max_dd > 0 else 0.0

    # Dynamic: best/worst sector by win rate
    sector_stats: dict = {}
    for r in resolved:
        sec = r.sector or "UNKNOWN"
        if sec not in sector_stats:
            sector_stats[sec] = {"wins": 0, "total": 0}
        sector_stats[sec]["total"] += 1
        if (r.pnl_pct or 0.0) > 0:
            sector_stats[sec]["wins"] += 1
    best_sector = "N/A"
    worst_sector = "N/A"
    if sector_stats:
        best = max(sector_stats.items(), key=lambda kv: kv[1]["wins"] / kv[1]["total"])
        worst = min(sector_stats.items(), key=lambda kv: kv[1]["wins"] / kv[1]["total"])
        best_sector = best[0] if best[1]["total"] > 0 else "N/A"
        worst_sector = worst[0] if worst[1]["total"] > 0 else "N/A"

    # Dynamic: strategy leaderboard grouped by setup_type
    strategy_stats: dict = {}
    for r in resolved:
        st = r.setup_type or "UNKNOWN"
        if st not in strategy_stats:
            strategy_stats[st] = {"wins": 0, "total": 0, "gross_profit": 0.0, "gross_loss": 0.0}
        strategy_stats[st]["total"] += 1
        pnl = r.pnl_pct or 0.0
        if pnl > 0:
            strategy_stats[st]["wins"] += 1
            strategy_stats[st]["gross_profit"] += pnl
        else:
            strategy_stats[st]["gross_loss"] += abs(pnl)
    leaderboard = []
    for st, s in strategy_stats.items():
        wr = round((s["wins"] / s["total"]) * 100, 1) if s["total"] > 0 else 0.0
        pf = round(s["gross_profit"] / s["gross_loss"], 2) if s["gross_loss"] > 0 else (round(s["gross_profit"], 2) if s["gross_profit"] > 0 else 0.0)
        leaderboard.append({
            "setup_type": st,
            "win_rate": wr,
            "profit_factor": pf,
            "ev_pct": ev_pct,
            "wins": s["wins"],
            "trades": s["total"],
        })
    leaderboard.sort(key=lambda x: x["win_rate"], reverse=True)

    return {
        "total_predictions": total_count,
        "resolved_predictions": n,
        "win_rate": win_rate,
        "avg_error": 0.0,
        "profit_factor": profit_factor,
        "empirical_rr_ratio": empirical_rr,
        "expected_value_pct": ev_pct,
        "max_drawdown_pct": max_drawdown_pct,
        "best_sector": best_sector,
        "worst_sector": worst_sector,
        "avg_confidence": avg_conf,
        "recent_outcomes": recent,
        "leaderboard": leaderboard,
    }

@router.post("/predictions/{prediction_id}/resolve", response_model=dict)
def resolve_prediction(
    prediction_id: int,
    req: PredictionResolveRequest,
    db: Session = DbDep,
    _=SessionDep,
) -> dict:
    pred = db.query(PredictionsHistory).filter(PredictionsHistory.id == prediction_id).first()
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found")

    exit_price = req.exit_price or (pred.target_price if req.actual_outcome == "TARGET_HIT" else pred.stop_loss)
    
    # Calculate PnL percentage
    if pred.entry_price and pred.entry_price > 0:
        if pred.prediction_type == "BULLISH":
            pnl_pct = ((exit_price - pred.entry_price) / pred.entry_price) * 100.0
        else:
            pnl_pct = ((pred.entry_price - exit_price) / pred.entry_price) * 100.0
    else:
        pnl_pct = 0.0

    pred.status = "RESOLVED"
    pred.actual_outcome = req.actual_outcome
    pred.pnl_pct = round(pnl_pct, 2)
    pred.resolved_at = datetime.now(timezone.utc).isoformat()

    db.commit()
    db.refresh(pred)

    return {
        "id": pred.id,
        "status": pred.status,
        "actual_outcome": pred.actual_outcome,
        "pnl_pct": pred.pnl_pct,
        "resolved_at": pred.resolved_at,
    }
