"""Market briefing router — composes the Daily Market Briefing card.

Honesty contract: every number in the briefing is computed from the live
signal-scan pipeline. When feeds cannot serve enough data, the route returns
HTTP 200 with `status: "unavailable"` — never invented values.
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Request
from app.api.deps import SessionDep
from app.core.limiter import limiter
from app.core.config import settings

router = APIRouter(prefix="/api", tags=["briefing"])

BRIEF_TIMEOUT_SECONDS = 10


def _unavailable(message: str) -> dict:
    """Honest empty briefing — no fabricatured numbers, client renders the text."""
    return {
        "status": "unavailable",
        "message": message,
        "briefing_text": message,
        "nifty_trend": None,
        "market_sentiment_pct": None,
        "top_opportunities": [],
        "risk_events": [],
    }


def _compose_brief() -> dict:
    """Runs in a worker thread: scan the NSE watchlist and extract real metrics."""
    from app.services.signal_engine import NSE_WATCHLIST, run_scan

    universe = list(NSE_WATCHLIST)
    results = run_scan(universe, "15m", "Intraday Momentum", "Medium", "NSE", 100_000.0)
    if not results:
        return _unavailable(
            "Daily Market Briefing unavailable: the market data feeds returned no "
            "scannable candles right now. Nothing is being made up — tap RETRY shortly."
        )

    scanned = len(results)
    above_ema21 = sum(
        1 for r in results if (r.get("price") or 0) > (r.get("ema21") or 0)
    )
    breadth_pct = int(round(above_ema21 / scanned * 100))
    if breadth_pct > 50:
        bias = "BULLISH"
    elif breadth_pct < 50:
        bias = "BEARISH"
    else:
        bias = "BALANCED"

    buy_setups = [r for r in results if r.get("signal") in ("BUY", "WEAK BUY")]
    sentiment_pct = int(round(len(buy_setups) / scanned * 100))

    top_rows = sorted(results, key=lambda r: r.get("confidence", 0), reverse=True)[:4]
    top_opportunities = [
        {
            "symbol": str(r["symbol"]).replace(".NS", ""),
            "signal": str(r.get("signal", "")),
            "confidence": int(r.get("confidence", 0)),
        }
        for r in top_rows
    ]

    missing = len(universe) - scanned
    data_note = (
        f" {missing} of {len(universe)} tracked symbols had no scannable data and "
        "are excluded from every number below." if missing > 0 else ""
    )

    briefing_text = (
        f"Engine scan on {scanned} of {len(universe)} tracked NSE symbols (15m bars): "
        f"{above_ema21}/{scanned} above their EMA21 ({breadth_pct}% breadth) → "
        f"{bias} bias. {len(buy_setups)} BUY-type setups detected; top picks below are "
        f"ranked by the engine's highest confidence."
        f"{data_note}"
    )

    return {
        "status": "ok",
        "nifty_trend": bias,
        "market_sentiment_pct": sentiment_pct,  # % of scanned symbols with BUY-type signal
        "top_opportunities": top_opportunities,
        "briefing_text": briefing_text,
        "risk_events": [],  # no macro calendar source exists; nothing is invented
    }


@router.get("/market_brief", response_model=dict)
@limiter.limit(settings.rate_limit_user)
async def get_market_brief(
    request: Request,
    _=SessionDep,
) -> dict:
    """
    Daily Market Briefing for the home panel.

    Feeds its numbers from the live signal-scan pipeline with a hard 10s
    backend timeout. When data is unavailable (feeds down, scan empty, timeout)
    responds 200 with an honest unavailable message — the client shows exactly
    that text.
    """
    loop = asyncio.get_running_loop()
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(None, _compose_brief),
            timeout=BRIEF_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        from app.core.logging import logger

        logger.warning("[briefing] composition timed out after 10s")
        return _unavailable(
            "Daily Market Briefing timed out after 10s — the scan didn't finish. "
            "Nothing is being made up; tap RETRY shortly."
        )
    except Exception as exc:
        from app.core.logging import logger

        logger.warning(f"[briefing] composition failed: {exc}")
        return _unavailable(
            "Daily Market Briefing is unavailable right now — nothing is being "
            "made up; tap RETRY shortly."
        )
