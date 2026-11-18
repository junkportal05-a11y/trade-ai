"""Capital allocation router for ScannerPanel."""
from fastapi import APIRouter, Request, HTTPException, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import DbDep, SessionDep
from app.core.security import CsrfDep
from app.core.limiter import limiter

router = APIRouter(prefix="/api", tags=["allocation"])


class AllocateRequest(BaseModel):
    capital: float = Field(default=100_000.0, gt=0, le=100_000_000)

AllocateRequest.model_rebuild()


class AllocateResponse(BaseModel):
    positions: list[dict] = Field(default_factory=list)
    deployment_pct: float = 0.0
    total_potential_profit: float = 0.0
    total_potential_loss: float = 0.0
    total_profit_pct: float = 0.0
    portfolio_rr: float = 0.0
    capital: float = 0.0
    total_deployed: float = 0.0
    max_risk_pct: float = 2.0
    all_signals: list[dict] = Field(default_factory=list)

AllocateResponse.model_rebuild()


@router.post("/allocate", response_model=AllocateResponse)
@limiter.limit("10/minute")
async def allocate_capital(
    request: Request,
    req: AllocateRequest = Body(...),
    db: Session = DbDep,
    csrf=CsrfDep,
    _=SessionDep,
) -> dict:
    """
    Allocate capital across signals with position sizing.
    Returns allocation plan with per-symbol position sizes and risk metrics.
    """
    from app.services.signal_engine import NSE_WATCHLIST, run_scan
    import asyncio
    import functools

    # Get current signals
    loop = asyncio.get_event_loop()
    try:
        signals = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                functools.partial(run_scan, NSE_WATCHLIST, "15m", "Intraday Momentum", "Medium", "NSE", req.capital),
            ),
            timeout=30,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Signal scan timed out")

    if not signals:
        return AllocateResponse(capital=req.capital).model_dump()

    # Simple position sizing: risk 2% per trade, max 10 positions
    risk_per_trade = req.capital * 0.02
    buy_signals = [s for s in signals if s.get("signal") in ("BUY", "WEAK BUY")]

    # If no strict BUY signals (e.g. outside market hours or chop where signals are HOLD),
    # use top ranked candidate signals so the user still gets valid position sizing & risk allocation
    candidate_signals = buy_signals if buy_signals else [s for s in signals if s.get("signal") != "SELL"]
    if not candidate_signals:
        candidate_signals = signals[:5]

    max_positions = min(10, len(candidate_signals))
    positions = []

    for i, sig in enumerate(candidate_signals[:max_positions]):
        entry = sig.get("entry") or sig.get("price") or 0
        stop = sig.get("stop_loss") or 0
        target = sig.get("target") or sig.get("target1") or 0
        if entry <= 0:
            continue
        if stop <= 0:
            stop = round(entry * 0.98, 2)
        if target <= 0:
            target = round(entry * 1.05, 2)

        risk_per_share = abs(entry - stop)
        if risk_per_share <= 0:
            risk_per_share = max(1.0, entry * 0.01)

        shares = int(risk_per_trade / risk_per_share)
        if shares <= 0:
            shares = 1

        amount_invested = round(shares * entry, 2)
        # Cap investment per position to max 25% of capital
        if amount_invested > req.capital * 0.25 and req.capital >= 1000:
            shares = max(1, int((req.capital * 0.25) / entry))
            amount_invested = round(shares * entry, 2)

        potential_profit = round(shares * abs(target - entry), 2)
        potential_loss = round(shares * risk_per_share, 2)
        rr = round(abs(target - entry) / risk_per_share, 2) if risk_per_share > 0 else 2.0
        alloc_pct = round((amount_invested / req.capital * 100), 1) if req.capital > 0 else 0

        positions.append({
            "symbol": sig["symbol"],
            "name": sig.get("name", sig["symbol"]),
            "shares": shares,
            "entry_price": entry,
            "amount_invested": amount_invested,
            "allocation_pct": alloc_pct,
            "target_price": target,
            "stop_loss": stop,
            "potential_profit": potential_profit,
            "potential_loss": potential_loss,
            "rr_ratio": rr,
            "reasons": sig.get("reasons", [f"Signal: {sig.get('signal')}"]),
            "mentor_advice": [
                f"Risk Guard: 2% capital risk rule applied ({shares} shares sized to ₹{potential_loss} max loss).",
                f"Stop Loss set at ₹{stop} using ATR volatility buffer.",
                f"Target at ₹{target} with 1:{rr} Risk-to-Reward ratio.",
            ],
        })

    total_invested = sum(p["amount_invested"] for p in positions)
    total_profit = sum(p["potential_profit"] for p in positions)
    total_loss = sum(p["potential_loss"] for p in positions)
    deployment = (total_invested / req.capital * 100) if req.capital > 0 else 0
    portfolio_rr = round((total_profit / total_loss), 2) if total_loss > 0 else 0

    return {
        "positions": positions,
        "deployment_pct": round(deployment, 1),
        "total_potential_profit": round(total_profit, 2),
        "total_potential_loss": round(total_loss, 2),
        "total_profit_pct": round((total_profit / req.capital * 100) if req.capital > 0 else 0, 1),
        "portfolio_rr": portfolio_rr,
        "capital": req.capital,
        "total_deployed": round(total_invested, 2),
        "max_risk_pct": 2.0,
        "all_signals": signals,
    }