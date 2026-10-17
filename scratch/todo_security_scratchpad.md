# Core Build: Order Execution Layer 🏗️

## Reality check (confirmed by direct grep, not assumed)

`place_order()` in `angelone_feed.py` is a stub:

```python
def place_order(self, order_params: Dict) -> Dict:
    logger.warning("Order execution not yet implemented")
    return {"status": "error", "message": "Not implemented"}
```

**Nothing in the entire codebase calls it.** `_square_off_all`, the signal scanner, and the resolver all work by comparing a live AngelOne **quote** against a stored `entry_price`/`target`/`stop_loss` and computing P&L on paper — no real order is ever sent to the broker anywhere today. This is a signal generator with real market data and simulated fills, not a trading bot with one missing method. "Build core" = design and wire an entire order-management layer that doesn't exist yet.

**Correction to an earlier claim in this audit:** it was previously reported that the resolver worker "silently falls back to entry_price" on broker disconnect. Direct read of `_square_off_all` shows this is false — it correctly `raise RuntimeError(...)` if `feed.is_authorized()` is false. Fail-loud, done right. Don't re-flag this as a bug.

---

## Phase 1 — Paper trading (build first)

- [x] Add `TRADING_MODE` to `Settings` (`config.py`): default `"paper"`, strictly validates `"paper"` or `"live"` with hard-fail on invalid values.
- [x] Add `LIVE_TRADING_ARMED: bool` (default `False`) as a **second, independent gate** — evaluated at runtime inside `place_order`.
- [x] Implement `place_order` as a dispatcher:
  - If `TRADING_MODE != "live"` OR `LIVE_TRADING_ARMED is not True` → routes to `_paper_fill()` with clear warning log.
  - Paper path: uses `get_live_quotes` + dynamic slippage model (`_compute_slippage_pct` scaled by stop-distance, 0.05-1.0% cap), returning simulated `placeOrderFullResponse` shape.
  - Idempotency key `PAPER-{pred_id}-{action}-{symbol}` enforced derived from prediction ID.
- [x] Add `order_mode` column to `models.py` (non-nullable, default `"paper"`), migration backfilled in `migrations.py`, and repository methods updated.
- [x] **Lifecycle Traced & Wired**: Signal -> position -> resolver flow mapped.
- [x] Tests completed: `backend/tests/test_order_dispatcher.py` (12/12 passed, 100% mocked SmartConnect).

---

## Phase 2 — Live trading (only after Phase 1 is proven)

- [ ] Real `self.smart_api.placeOrderFullResponse(...)` call, using the existing `api.search.scrip` symbol→token lookup (already implemented elsewhere in `angelone_feed.py` — reuse, don't reimplement).
- [ ] Minimum bar before flipping `LIVE_TRADING_ARMED`, in order:
  1. `place_order` proven correct in paper mode across real market hours, multiple symbols, both directions (BULLISH/BEARISH)
  2. Broker-disconnect handling on the *manual* resolve path confirmed to fail loud (see 2.4)
  3. Shared single-`angelone_sessions`-row race condition addressed — right now any authenticated account can overwrite the one shared broker session; this becomes a real-money race condition once orders are live, not just an inconvenience
  4. `signals_history`/`angelone_sessions` RBAC sweep (3.1) completed
  5. Extended unattended paper-trading run (weeks, not days) with fills/resolver outcomes manually cross-checked against reality
