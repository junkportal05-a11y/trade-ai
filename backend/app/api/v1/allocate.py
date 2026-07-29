"""Capital allocation router for ScannerPanel."""
from fastapi import APIRouter, Request, Depends, HTTPException, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import DbDep, OptionalSessionDep
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

AllocateResponse.model_rebuild()


@router.post("/allocate", response_model=AllocateResponse)
@limiter.limit("10/minute")
async def allocate_capital(
    request: Request,
    req: AllocateRequest = Body(...),
    db: Session = DbDep,
    _=OptionalSessionDep,
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
        return AllocateResponse().model_dump()

    # Simple position sizing: risk 2% per trade, max 10 positions
    risk_per_trade = req.capital * 0.02
    max_positions = min(10, len([s for s in signals if s.get("signal") in ("BUY", "WEAK BUY")]))

    buy_signals = [s for s in signals if s.get("signal") in ("BUY", "WEAK BUY")]
    positions = []

    for i, sig in enumerate(buy_signals[:max_positions]):
        entry = sig.get("entry") or sig.get("price") or 0
        stop = sig.get("stop_loss") or 0
        target = sig.get("target") or 0
        if entry <= 0 or stop <= 0:
            continue

        risk_per_share = abs(entry - stop)
        if risk_per_share <= 0:
            continue

        shares = int(risk_per_trade / risk_per_share)
        if shares <= 0:
            continue

        amount_invested = shares * entry
        potential_profit = shares * abs(target - entry) if target > 0 else 0
        potential_loss = shares * risk_per_share

        rr = abs(target - entry) / risk_per_share if risk_per_share > 0 else 0

        positions.append({
            "symbol": sig["symbol"],
            "name": sig.get("name", sig["symbol"]),
            "shares": shares,
            "entry_price": entry,
            "amount_invested": round(amount_invested, 2),
            "target_price": target,
            "stop_loss": stop,
            "potential_profit": round(potential_profit, 2),
            "potential_loss": round(potential_loss, 2),
            "rr_ratio": round(rr, 2),
            "reasons": sig.get("reasons", [f"Signal: {sig.get('signal')}"]),
        })

    total_invested = sum(p["amount_invested"] for p in positions)
    total_profit = sum(p["potential_profit"] for p in positions)
    total_loss = sum(p["potential_loss"] for p in positions)
    deployment = (total_invested / req.capital * 100) if req.capital > 0 else 0
    portfolio_rr = (total_profit / total_loss) if total_loss > 0 else 0

    return {
        "positions": positions,
        "deployment_pct": round(deployment, 1),
        "total_potential_profit": round(total_profit, 2),
        "total_potential_loss": round(total_loss, 2),
        "total_profit_pct": round((total_profit / req.capital * 100) if req.capital > 0 else 0, 1),
        "portfolio_rr": round(portfolio_rr, 2),
    }