# ApexTrade — Production Readiness Report

**App:** ApexTrade — NSE Intraday Signals (private, single-user, paper-only trading workstation)
**Live URL:** https://trade-ai-beta.vercel.app/
**Backend:** https://apextrade-core-trade-ai-backend.hf.space (Vercel rewrites `/api/*` to it)
**Version checked:** v6.1.1
**Date of check:** Thursday 19 November 2026, ~13:25–13:30 IST
**Repo checked:** github.com/junkportal05-a11y/trade-ai, HEAD `998bb76` (18 Nov 2026, 21:51 UTC)
**Checked by:** Muse — live UI walkthrough (signed-in session), unauthenticated endpoint probes, read-only GitHub code audit

---

## Verdict

**NOT production ready** — as an autonomous paper-trading system, which is the app's stated Phase 1 purpose.

It **is safe as a gated paper dashboard**: the site loads, the login gate holds, paper-only mode is locked in at several layers, and no live money can move. But the core job of the app — running the bot on simulated ticks and building a validated record of paper trades — cannot happen yet, because the backend workers that do it are disabled and the two places a user would watch results (Terminal chart, Trade Log) do not load.

### What "production ready" means for this app

Phase 1 = autonomous paper trading that builds a large validated record of real outcomes, so a model can later be trained on it. Production ready therefore means: the bot runs in paper mode, paper trades actually get logged, charts and logs display them, data is labelled honestly (simulated vs real), and nothing errors. It does **not** mean live trading or SEBI compliance — live trading must stay off, and no SEBI compliance is claimed.

---

## How it was checked

| Check | Method | Limits |
|---|---|---|
| Live UI | Clicked through all 7 sections in the user's own signed-in Chrome tab | Read-only. Did not press START BOT, did not press ANALYZE & PREDICT, did not press RETRY on the chart, did not run a backtest, did not change any setting, did not enter any access code |
| Endpoints | curl probes, read-only, no sign-in | Unauthenticated only. Anything behind the login (chat, briefing content, predictions, journal) could only be checked for its auth behaviour, not its content |
| Code | Read-only audit of the GitHub repo at HEAD `998bb76` | Read-only. No fixes made. Scan covered files fetched via the connector, not a full-history secret scan |

---

## 1. Live system snapshot (13:25 IST, 19 Nov 2026)

| Item | Observed |
|---|---|
| Site | HTTP 200, title "ApexTrade — NSE Intraday Signals", loads in ~1.25s |
| Version | v6.1.1, environment `production` |
| Health | `status: "degraded"` (honest), total latency 0.4ms |
| Database | PostgreSQL healthy, 0.27ms, pool 5/5 |
| Quant server | Connected, "NSE OPEN", health-check ~229–245ms |
| Market feed | `SIMULATED`, "FEED: SYNCHRONIZED", latency 11ms, prices ticking (e.g. RELIANCE ₹100.06, TCS ₹99.99, INFY ₹99.95) |
| AI services | Gemini and News API both `not_configured` — local fallback only |
| Workers | `trading_agent_loop`, `prediction_resolver_worker`, `governance_loop` — **all disabled** |
| Broker | `paper_no_broker`, `live_armed: false` |
| Data folders | `knowledge_dir` and `historical_data_dir` do not exist on the backend host (storage warning) |
| Disk | 79.7% used, 344 GB free |
| Prices endpoint | Returns 200, but `"simulated": true`, `"data_source": "SIMULATED"` — no live market data |

---

## 2. UI / UX — section by section

### Header and navigation (all pages)

- **Working:** Top ticker bar "NSE TICK FEED / SIMULATED" ticks live, "FEED: SYNCHRONIZED", "LATENCY: 11ms". Navigation renders: Home, Bot Engine, Terminal, Scanner, Predictions, Analytics, Journal, Security, MORE.
- **Not working:** No chart or graph rendered in any section checked.

### Bot Engine

- **Working:** "Bot Engine Control Matrix" loads. Status STOPPED, PAPER RUNTIME. Today's P&L +₹0.00, Active Signals 0, Daily Stop Loss ₹2,500.00, Safety Circuit ARMED. START BOT visible (not pressed); PAUSE and STOP ALL disabled. 5 strategies listed, all ENABLED: Trend Scalper, Mean Reversion, Breakout Volume, RSI Scalper, Swing Trend Follower. Backtest Engine form renders (RELIANCE, Intraday Momentum, 01-01-2024 to 31-12-2024, Capital ₹100,000, Stop ATR Mult 1.5). 30-strategy leaderboard renders (32 rows, "BEST: Money Flow Index (MFI 14 Reversals) (SCORE: 16)").
- **Not working:** Trade Log panel ("Paper Bot Decisions (simulated prices)") stuck on "Loading trade log..." with a spinning indicator on two separate visits (13:24 and 13:26 IST) — no entries ever appear.
- **UX issue:** The Trend Scalper card renders with a white background and washed-out, low-contrast text; its win-rate is not legibly visible.

### Terminal

- **Working:** Controls render: RELIANCE ₹100.02 (+0.02%), "CANDLE 1m", indicators EMA9 ₹100.02, EMA21 ₹100.02, VWAP ₹100.02, RSI(14) 53. POSITIONS tab: "NO ACTIVE POSITIONS HELD", NET WORTH ₹0.00, CASH ₹0.00, INVESTED ₹0.00. Portfolio / P&L / Cash / Holdings all ₹0.00.
- **Not working:** The main chart **fails to load** — "Failed to load chart data. Tap RETRY to try again." with a RETRY button, a "SIMULATION MODE" watermark and "LOADING MARKET DATA..." text. No candlesticks or price chart render. The right-hand panel (tabs BOT ENGINE / TRADE LOG / STRATEGIES / BACKTEST) is a large empty black area with no visible content.
- **UX issue:** The error state exists (good), but the core view of the Terminal — the chart — is entirely missing.

### Scanner

- **Working:** Scan runs and finishes: briefly "SCANNING... 0% — Fetching live OHLCV for NSE intraday universe", then settles. Market Mood NEUTRAL, BUYS 0, SELLS 0, "0 STOCKS SCANNED", Capital ₹10,000, DEFAULT SCANNER, auto-rescan countdown "04:59". No endless spinner after the scan.
- **Not working:** Result is empty — "Market is closed. No active intraday setups detected on live feed." and "No ALL signals — No signals match the current filters."
- **UX issue (contradiction):** The header says "NSE OPEN" while the Scanner says "Market is closed". Both cannot be true; the user cannot tell which one to trust.

### Predictions

- **Working:** Page loads. "AI Prediction Engine", form renders (RELIANCE, 15m, Historical Deep Learning, Confidence Threshold 70%, "ANALYZE & PREDICT" button — not pressed). "AI MODEL READY" / "Ready to analyze RELIANCE".
- **Not working:** Everything is zero — TODAY'S PREDICTIONS 0, AVG CONFIDENCE 0%, PREDICTION LOG 0, ACCURACY 0%. "TODAY'S AI SIGNALS: No signals yet. Run the prediction engine to generate AI-powered buy/sell signals for today."
- **Unproven:** Whether ANALYZE & PREDICT actually produces a signal (not pressed during this check).

### Analytics

- **Working:** Six metric boxes render: Win Rate 0% (0 of 0 resolved), Average Return 0%, Total Signals 0, Resolved 0, Today's Signals 0, Open Signals 0. Labelled honestly: "DATA SOURCE: SIMULATED (no resolved predictions)", "Resolved trades: 0 of 0".
- **Not working:** Below the metric boxes is a large empty black area; scrolling reveals nothing more — no charts, graphs, tables or error message.

### Journal

- **Working:** Page loads. "Trade Journal & Position Tracker", TOTAL TRADES 0, WIN RATE 0%, TOTAL P&L ₹0.00, OPEN POSITIONS 0, filter tabs ALL/OPEN/CLOSED.
- **Not working:** Nothing to show — "NO TRADES YET — Start trading to see your journal entries here." (Expected with zero trades, but it confirms no trade has ever been recorded.)

### Security

- **Working:** Page loads. "Security & Access Control". AngelOne Integration form renders with empty Client ID, API Key and PIN fields and "CONNECT ANGELONE" / "NOT CONNECTED". Security Hardening: "Session Timeout: 30 min", "Audit Logs: ENABLED". Audit & Activity Feed: "No security events recorded yet."
- **Open question:** The profile shown is **"Vishal Agnihotri — vishalagnihotri12@gmail.com — Trader — PRO ACCESS — Device: VSC-Desktop — Session: 0m (ACTIVE)"**. That is not the owner's name. Confirm whose session/profile this is — a leftover demo profile, or a real second identity on the account.

---

## 3. Features — working / not working / unproven

### Working

| Feature | Evidence |
|---|---|
| Site loads (v6.1.1, PAPER ONLY) | HTTP 200, ~1.25s |
| Auth gate on sensitive routes | Every sensitive route returns 401 unauthenticated; only `/`, `/api/health`, `/api/prices` are open |
| Health reporting | Honest `degraded` status, DB healthy |
| Simulated price feed | Ticks, synchronized, 11ms |
| Backtest leaderboard renders | 32 rows, best strategy labelled |
| Scanner completes a scan | Finishes, no endless spinner |
| Forms render (backtest, prediction, AngelOne) | All present and legible |
| Paper-only safety gates | `live_armed: false`, no broker, boot refuses live mode, bot/start rejects live, order function has zero callers |
| No secrets committed | No `.env` in the tree at HEAD; `.env` never actually committed despite a commit message claiming it; AngelOne credentials Fernet-encrypted before storage |

### Not working

| Feature | Evidence |
|---|---|
| Autonomous paper trading | All 3 workers disabled in live health response; bot STOPPED; 0 trades, 0 signals, ₹0.00 everywhere |
| Terminal chart | "Failed to load chart data", no candles |
| Trade Log | Stuck on "Loading trade log..." across two visits |
| Live market data | Prices endpoint is simulated only |
| AI | Gemini + News API not configured; local fallback only |
| Scanner vs header | "Market is closed" vs "NSE OPEN" |
| Analytics charts | Large blank black area, no charts |
| Data folders | `knowledge_dir`, `historical_data_dir` missing on backend host |

### Unproven (could not be verified without signing in or pressing a button)

| Feature | Why unproven |
|---|---|
| Chat | POST `/api/chat` returns 403 "CSRF token required" unauthenticated (the October 500 is gone, but whether chat works behind a valid session is unknown). Also slow: 6–10s |
| Briefing content | Real route is `/api/market_brief`, auth-gated (401 unauthenticated); content unverified |
| Prediction generation | ANALYZE & PREDICT not pressed |
| Backtest run | Form renders; a run was not executed |
| Bot start | START BOT not pressed |
| Trade logging end to end | No trade exists to verify the logging path live |

---

## 4. Endpoints (unauthenticated probes)

| Endpoint | Status | Notes |
|---|---|---|
| GET `/` | 200 | SPA shell, 3.2 KB, title correct |
| GET `/api/health` (Vercel + HF direct) | 200 | Identical payload — Vercel is a straight rewrite to HF |
| GET `/api/prices` (Vercel + HF) | 200 | Simulated data only |
| POST `/api/chat` | 403 | `{"detail":"CSRF token required"}` — gate, not a success |
| GET `/api/chat` | 405 | Method Not Allowed |
| GET `/api/briefing`, `/api/brief` | 404 | Not Found on both Vercel and HF |
| GET `/api/market_brief`, `/api/predictions`, `/api/predictions/stats`, `/api/data/confidence`, `/api/backtest/tournament/leaderboard`, `/api/journal`, `/api/history` | 401 | `{"detail":"Authentication required"}` — gate holds |
| GET `/api/auth/verify` (no token) | 401 | `{"detail":"Invalid token"}` |

Minor: the frontend JS bundle still references stale `http://127.0.0.1`, `http://localhost` and `https://my-backend.hf.space` URLs alongside the live HF backend.

---

## 5. Code audit — the four October 2026 blockers

All four blockers found in the 27 Oct 2026 finish run are **fixed in the code at HEAD `998bb76`**. The gap is that the live deployment's parity with this HEAD is **unverified**.

| October blocker | Status in code | Evidence | Live status |
|---|---|---|---|
| POST /api/chat 500s | Fixed, with one latent 500 path | `backend/app/api/v1/chat.py:16-31` → `get_chat_reply()` in `backend/app/services/chat.py`; Gemini → local LLM → deterministic heuristic fallback, all wrapped in try/except, never raises | 403 CSRF unauthenticated; works-or-not behind login unproven |
| Bot paper-trade logging (`prediction_type` omitted) | Fixed | `backend/trading_agent.py:299` calls `db.add_prediction(_build_prediction_payload(sig))`; builder `:487-491` includes `"prediction_type": "BULLISH"` / `"BEARISH"`; `:522` sets `"order_mode": "paper"`; `backend/db.py:573-588` inserts it; schema validates it (`backend/app/models/schemas.py:162-174`) | Unproven live — no trade has ever been logged |
| Briefing route absent | Exists now | `backend/app/api/v1/briefing.py:95-97`, `GET /api/market_brief` (not `/api/briefing`), registered in `backend/app/api/v1/router.py:16`; 10s hard timeout; on empty feeds/timeout returns HTTP 200 with `status: "unavailable"` and no invented numbers | Route exists behind auth; content unproven |
| yfinance MultiIndex chart 404s | Fixed | `backend/signals.py:70-74` `_flatten_columns()` applied at every data tier: cache `:292`, AngelOne `:304`, yfinance `:324` (plus rename `:325-332`), last-good snapshot `:349`; also inline `:1387-1388`, `:1419-1420` | Chart still fails to load live — cause is not the MultiIndex flattening; needs live diagnosis |

### Latent issues found in code (not yet live failures)

1. **`source='litellm'` 500:** `backend/app/services/chat.py:272` sets `parsed['source'] = 'litellm'`, but `ChatResponse` (`backend/app/models/schemas.py:119-123`) only allows `Literal["gemini", "heuristic"]`. If a local LLM is ever configured (`LITELLM_API_BASE` / `OLLAMA_BASE_URL`), a valid LLM reply fails FastAPI response validation → 500. One-line fix: add `"litellm"` to the Literal, or map it to `"heuristic"`. Does not trigger in the current config (no AI configured → heuristic path).
2. **Synthetic-data fallback tier:** `backend/signals.py` Tier 4 is a synthetic candle generator — when all real feeds fail, the pipeline serves generated candles, labelled `"synthetic"` in `_SOURCE_CACHE`. Anything downstream that presents scan/chart data as real market data must surface that label.
3. **Minor:** `db.py:588` uses `pred["prediction_type"]` (KeyError if a future caller omits it); only one caller exists today. `db.add_prediction` (`db.py:615-620`) would store `order_mode="live"` if a caller passed it; only the bot calls it, always with `"paper"`.
4. **Two entry points:** `backend/Procfile` → `uvicorn main:app`, `backend/Dockerfile` → `uvicorn app.main:app`. Which one the live HF backend actually runs is unverified — this is why HEAD-vs-live parity cannot be confirmed from the repo alone.
5. **Repo visibility:** the GitHub API reports the repo as **public** (`private: false`). The October record said private. Confirm which is correct — if public, the code is visible to anyone (the app itself is still login-gated).

### Auth gate (code)

- Single user only: `apex_head_quant`, `LEVEL_4_ROOT`, password from `PASS_ADMIN` / `APP_PASSWORD` env, bcrypt-hashed at runtime (`backend/app/core/security.py:186-199`). `authenticate_by_code` (`:220-228`) matches a code against that single hash. No signup, roles, or multi-user code.
- `POST /api/login` (`backend/app/api/v1/auth.py:24-71`) sets HttpOnly `apt_token` JWT cookie + `apt_csrf`; `GET /api/auth/verify` at `auth.py:93-114`. In production, a missing `PASS_ADMIN` raises at boot (fail-closed, `security.py:190`); in dev a random ephemeral code is generated.
- Auth/DB dependency errors fail closed to 401, not 500 (`security.py:118-125`).

### Live-trading safety (code)

- `trading_mode` defaults `"paper"`, `live_trading_armed` defaults `False` (`backend/app/core/config.py:210-211`); the app **refuses to boot** if `live_trading_armed` is true (`:146-150`, SEBI review gate).
- `POST /api/bot/start` rejects `paper=false` or `order_mode="live"` with 400 (`backend/app/api/v1/bot.py:36-39`).
- `place_order` exists (`backend/angelone_feed.py:942-980`) and can route live only when `trading_mode == "live"` and `live_trading_armed` (`:965`) — but it has **zero callers** anywhere in the codebase, and the boot gate makes the live branch unreachable. Dead code behind a hard gate. Broker login wiring (`backend/app/api/v1/broker.py`) exists for data-feed session only.

---

## 6. UI / UX issues (design)

1. **Trend Scalper card** — white background, washed-out low-contrast text, win-rate illegible. (Only card with this problem; the other four strategy cards render normally.)
2. **Blank black panels** — Terminal right-hand panel and the lower half of Analytics are large empty black areas with no content, no chart, no empty-state message.
3. **No charts anywhere** — not one chart or graph rendered in any of the seven sections during this check.
4. **Scanner vs header contradiction** — "Market is closed" vs "NSE OPEN".
5. **Trade Log spinner with no timeout** — "Loading trade log..." spins forever with no error and no empty state.
6. **Chart error state** — the Terminal does show a proper error ("Failed to load chart data. Tap RETRY"), which is the right pattern; the problem is the data behind it, not the message.

---

## 7. Open questions (need the owner)

1. Security page shows profile **Vishal Agnihotri — vishalagnihotri12@gmail.com**. Whose session/profile is this?
2. Is the GitHub repo public or private? (API says public; October record said private.)
3. Is the live HF backend running HEAD `998bb76`, or an older/newer commit? (Two entry points in the repo make this unprovable from code alone.)
4. Is the missing `knowledge_dir` / `historical_data_dir` expected on the HF host, or should those folders be created/restored?

---

## 8. Fix list, in priority order

1. **Enable the three workers** (`trading_agent_loop`, `prediction_resolver_worker`, `governance_loop`), start the bot in paper mode, and verify **one paper trade logs end to end** (prediction logged with `prediction_type`, visible in Trade Log and Journal). Until this works, Phase 1 does not exist.
2. **Fix the Terminal chart load failure** and the **Trade Log stuck loading** — diagnose live (these are not the old MultiIndex bug; the code fix for that is already in).
3. **Prove live = HEAD `998bb76`** — resolve the two-entrypoint question and confirm the deployed bundle matches the repo.
4. **Fix the Scanner vs header contradiction** and surface the synthetic-data label wherever simulated/synthetic data is shown as market data.
5. **Configure AI** (Gemini key) or formally accept local-fallback-only; fix the latent `source='litellm'` 500 at the same time.
6. **Restore `knowledge_dir` and `historical_data_dir`** on the backend host (or confirm they are intentionally absent).
7. **Confirm repo visibility** (public vs private) and the **Security page profile name**.
8. **Minor UI:** fix the Trend Scalper card contrast; give the blank Analytics/Terminal panels a real empty state or hide them; remove stale localhost URLs from the JS bundle.

---

## Appendix — what was NOT tested

- START BOT, ANALYZE & PREDICT, chart RETRY, and running a backtest were deliberately not pressed (read-only check).
- Chat, briefing content, predictions, journal and history behind the login were not verified (unauthenticated probes can only confirm the gate).
- The access-code login step itself was not tested (owner-tested only, by standing rule).
- No code was changed, no deployment was made, no trade was placed, no payment was involved.
