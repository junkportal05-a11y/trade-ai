# ApexTrade Security & Order Execution Roadmap Scratchpad

---

## 🎯 Phase 1 — Paper Trading & Order Execution Layer (Build First)

- [x] **1. Add `TRADING_MODE` to Settings (`backend/app/core/config.py`)**
  - Default: `"paper"`
  - Allowed: `"paper"` or `"live"` strictly.
  - Fail-loud: Hard-fail on any other value in all environments (matches `JWT_SECRET` fail-fast validation).

- [x] **2. Add `LIVE_TRADING_ARMED: bool` Setting (`backend/app/core/config.py`)**
  - Default: `False`
  - Acts as a second, independent runtime gate — checked inside `place_order` at call time (not just during startup load).
  - Ensures live trading cannot be enabled by a single accidental env-var flip.

- [x] **3. Implement `place_order` Dispatcher (`backend/angelone_feed.py` / Execution Service)**
  - Guard logic: If `TRADING_MODE != "live"` OR `LIVE_TRADING_ARMED is not True` → execute paper path regardless of caller request.
  - Warning: Log clear warning if live was requested-but-not-armed; never silently error out and never silently promote to live.
  - Paper path: Use dynamic slippage model (`stop_distance_pct * 0.15`, capped at 2% of entry) to compute fill price deviation; returns simulated fill shaped exactly like AngelOne's `placeOrderFullResponse` so calling code needs zero branching.
  - Format: `{"status": True, "message": "SUCCESS", "data": {"orderid": "..."}}` where orderid is deterministic from prediction_id + action + symbol.
  - Idempotency: Every order (paper or live) gets an idempotency key derived from prediction_id (prevents duplicate submissions on retries or double-triggered scans).

- [x] **4. Add `order_mode` Column to Orders / Fills Table**
  - Unambiguously tag `'paper'` vs `'live'` in every stored row (never a shared or nullable space where the tag can be dropped).
  - `backend/app/db/models.py`: `order_mode = Column(String(10), nullable=False, default="paper", server_default="paper")` on `PredictionsHistory`.
  - `backend/app/db/migrations.py`: added `("order_mode", "TEXT")` to `pred_columns`; backfill `UPDATE predictions_history SET order_mode = 'paper' WHERE order_mode IS NULL`.
  - `backend/app/db/repositories.py`: `PredictionRepository.add()` accepts `order_mode` param, defaults to `"paper"`.
  - `backend/tests/test_order_mode.py`: 8 tests, all pass (default, explicit paper/live, NOT NULL enforced, null insert rejected, backfill query correct, to_dict includes order_mode, paper/live distinct).

- [x] **5. Trace Existing Order & Position Flows Before Wiring**
  - Entry: `trading_agent.py:236` → `db.add_prediction()` (no fill_price/order_mode), `trading_agent.py:238` → `db.add_journal_entry()`.
  - Exit (square-off): `trading_agent.py:281-295` → `db.resolve_prediction()` using live quote price, no broker order sent.
  - Exit (resolver): `trading_agent.py:453-467` → `db.resolve_prediction()` using live quote price, no broker order sent.
  - **Gap**: PnL computed from live quotes, not actual fills. No `place_order` in entry or exit path. No `fill_price`/`slippage_pct` recorded.
  - Proposed: wire `place_order` before `db.add_prediction` (entry) and before `db.resolve_prediction` (exit).

- [ ] **6. Phase 1 Test Suite Verification**
  - Assert paper mode is always used when unarmed even if `TRADING_MODE="live"`.
  - Assert idempotency key blocks double-submission.
  - Assert paper/live tags are never ambiguous on stored orders.
  - Assert zero network calls to real AngelOne endpoints (SmartConnect mocked 100%).

---

## 🚀 Phase 2 — Live Trading Execution (After Phase 1 Proven)

- [ ] **1. Real `placeOrderFullResponse` Implementation**
  - Wire real `self.smart_api.placeOrderFullResponse(...)` call.
  - Reuse existing `api.search.scrip` symbol → token lookup from `angelone_feed.py`.

- [ ] **2. Mandatory Verification Bar Before Enabling `LIVE_TRADING_ARMED`**
  - [ ] `place_order` proven correct in paper mode across real market hours, multiple symbols, and both directions (`BULLISH`/`BEARISH`).
  - [ ] Broker disconnect on manual resolve confirmed fail-loud (HTTP 503).
  - [ ] Single `angelone_sessions` row race condition resolved (multi-user session scoping to prevent account session overwrites).
  - [ ] `signals_history` / `angelone_sessions` RBAC sweep finalized.
  - [ ] Extended unattended paper-trading run (weeks) with fill outcomes cross-checked against live market data.

---

## 🛡️ Security Audit Remediation Status (Parts 5, 6, 7)

- [x] **5.1 / 6.1: Remove `ProxyHeadersMiddleware(trusted_hosts=["*"])`**
  - Verified: Removed from `backend/app/main.py`. Real IP properly preserved without spoofing.
- [x] **5.2 / 6.2: Deduplicate `/api/backtest/run` Route**
  - Verified: Direct route removed from `main.py`; single rate-limited route active in `backend/app/api/v1/backtest.py`.
- [x] **5.3 / 6.3: n8n Webhook Secret & Error Sanitization**
  - Verified: `_require_n8n_secret` enforced with `secrets.compare_digest`, generic internal error responses returned.
- [x] **5.4 / 6.4: CSRF Header Protection**
  - Verified: `X-Requested-With: XMLHttpRequest` enforced across mutating routers; n8n machine routes properly exempted.
- [x] **5.5 / 6.5 / 7.3: WebSocket Auth Precedence**
  - Verified: Cookie (`apt_token`) first -> `?token=` query param fallback -> `Authorization: Bearer` header.
- [x] **5.6 / 6.6 / 7.4: Repomix Personal Vault Exclusions**
  - Verified: Excluded Obsidian personal vaults (`brain/`, `org/`, `perf/`, `daily/`, etc.) from `codebase.md`.
- [x] **7.1: Multi-Tenant Trade Journal Ownership**
  - Verified: `user_id` column added, migrations backfilled to `'legacy'`, `repositories.py` and `journal.py` strictly scoped by `session["username"]`.
- [x] **7.2: Predictions & Broker Routes Gated by `TraderDep`**
  - Verified: Mutating routes in `predictions.py` and `/api/angelone/login` in `broker.py` require `LEVEL_2_TRADER`.
- [x] **7.7: Tighten `exit_price` Tolerance Formula**
  - Verified: Formula in `predictions.py:222` set to `max(0.1, min(2.0, stop_pct * 0.15))` (1.5% on 100/110/90 setups). Tested in `test_manual_resolve.py`.
- [ ] **7.6: `angelone_sessions` Multi-User Scoping (Phase 2 Blocker)**
  - Open: Single shared session row needs user scoping before real-money multi-user live execution.

---

## 📌 Core Engineering Principles

1. **"Fail Loudly" Over "Swallow Instead of Fail"**: No silent fallbacks, no dual-signature shims, and no defensive isinstance workarounds to mask bad test calls.
2. **Verify Against Actual Code on Disk**: Claims, comments, and summaries are not truth — verify with direct file reads and test passes.
3. **Ownership vs Role-Based Gating**: Distinguish personal user data (Journal `user_id`) from shared system ledgers (Predictions, Signals).
4. **Trace Full Request Path**: Ensure middleware and dependencies do not silently cancel each other out.
5. **Direct Inspection Over Ambiguous Diffs**: When in doubt, read the full active file on disk.
