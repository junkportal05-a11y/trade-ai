# APEXTRADE AI — CODEBASE ARCHITECTURE & SYSTEM SPECIFICATION
> **Last Updated**: 2026-10-30 | **Clearance**: LEVEL_4_ROOT Exclusive | **Version**: 6.1.1 (backend `config.py` AND frontend `package.json` both 6.1.1) | **This run (TAR-21 deploy)**: backend pytest 296/0, frontend vitest 46/46, build 0 errors, HF Space live & probed — see §10b

---

## 1. 🏗️ SYSTEM ARCHITECTURE OVERVIEW

ApexTrade AI is an institutional-grade, personal algorithmic trading workstation and autonomous bot engine. It integrates real-time market data streaming, technical pattern analysis, multimodal chart scanning (Gemini 2.0 Flash), and autonomous order routing.

```
┌────────────────────────────────────────────────────────────────────────┐
│                      FRONTEND WORKSTATION                              │
│         React 19 + Vite 8 + Lightweight Charts 5 + Lucide SVG          │
│   • IntroSplash (/api/health handshake)  • Header (Market Beacon)      │
│   • CommandPalette (Ctrl+K)              • CandleChart (📸 AI Scan)    │
│   • ChatPanel (Prompt Chips & Gauges)    • BotControlPanel (Autonomous)│
│   • CodeEntryScreen (Single-code gate)   • Auth Gate (verifyToken)     │
│   • LandingPage (Public hero/features)   • Terms / Privacy / Disclaimer│
└─────────────────────────────────┬──────────────────────────────────────┘
                                  │ REST / WebSockets
                                  ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        QUANT ENGINE BACKEND                            │
│                 FastAPI + Python 3.12 + PostgreSQL                     │
│   • /api/health (Handshake in <1ms)      • /api/auth/verify (Gate)     │
│   • /api/chat/chart (Gemini AI)          • /api/scan & /api/bot        │
│   • /api/prices (Public)                 • /api/backtest (Protected)   │
│   • Trading Agent Worker Loop            • Prediction Resolver Worker  │
└─────────────────────────────────┬──────────────────────────────────────┘
                                  │
         ┌────────────────────────┴────────────────────────┐
         ▼                                                 ▼
┌───────────────────────────────┐ ┌──────────────────────────────────────┐
│       EXTERNAL BROKER         │ │       AUTOMATION & TESTING           │
│   Angel One SmartAPI (V2)     │ │   • Google Artemis (Mobile & ADB)    │
│   Live / Paper Order Routing  │ │   • BlueStacks 5 (emulator-5554)     │
│   AES-256 Fernet Encrypted    │ │   • Google Agents CLI (1.11.0)       │
└───────────────────────────────┘ └──────────────────────────────────────┘
```

---

## 2. 🔐 SECURITY & PERSONAL WORKSTATION MODE

* **Single-Code Gate**: All traditional multi-user login gates removed. Access controlled via a **single access code** (`POST /api/login` with `username="code"`).
* **JWT Session**: Token issued as `apt_token` cookie (httponly, secure, samesite=none, 8h TTL) + mirrored in `localStorage`/`sessionStorage` for `apiFetch`.
* **Token Verification**: Frontend calls `/api/auth/verify` on mount via `verifyToken()` in `api.js`; 401 from any `apiFetch` clears tokens and dispatches `apex:auth-required` to trigger `CodeEntryScreen`.
* **Exclusive Clearance**: Strictly bound to **`LEVEL_4_ROOT`** (`Master Quant / Administrator`). All lower tiers (`LEVEL_1_GUEST`, `LEVEL_2_TRADER`, `LEVEL_3_ADMIN`) retired.
* **Single User Registry**: Backend `UserRegistry` retains only `apex_head_quant`. Password loaded from `PASS_ADMIN`/`APP_PASSWORD` env (bcrypt-hashed at runtime).
* **Production Secrets Hardening** (`7a391e3`, v6.1.1): `security.py` raises `RuntimeError("CRITICAL SECURITY FAILURE")` if `PASS_ADMIN`/`APP_PASSWORD` is unset in production/staging. `config.py` hardens further: every configured `FERNET_KEYS` entry must actually construct+decrypt a sample — invalid keys **raise** in production/staging (only development regenerates), `DEBUG=True` outside development raises, a `DATABASE_URL` with `ENVIRONMENT` unset raises (its guards would silently not apply), and `live_trading_armed` is refused outright until the SEBI 2025 algo-trading review. `backend/.env*` is gitignored by intent — secrets never live in the repo or this doc.
* **Generic error shape** (`7a391e3`): unhandled exceptions return a generic body with `correlation_id` (middleware `X-Correlation-ID`, JSON logging joins server logs); internals leak nothing. Docs UI (`/docs`, `/redoc`, `/openapi.json`) disabled in production.
* **Broker Security**: Sensitive broker credentials (API key, client code, TOTP secret) encrypted with Fernet MultiFernet AES-256 before disk persistence.

---

## 3. 🌐 NETWORKING & HOSTING TARGETS

| Environment | Role | URL / Port |
|---|---|---|
| **Local Frontend** | Vite Dev Server | `http://127.0.0.1:5173/` or `http://localhost:5173/` |
| **Local Backend** | FastAPI Quant Server | `http://127.0.0.1:7860/` |
| **Local Proxy** | OpenRouter Proxy | `http://127.0.0.1:3000/` |
| **Production Backend** | Hugging Face Spaces | `https://apextrade-core-trade-ai-backend.hf.space` *(PUBLIC)* |
| **Production Frontend** | Vercel | `https://trade-ai-beta.vercel.app/` |
| **GitHub Source** | GitHub Repository | `https://github.com/junkportal05-a11y/trade-ai.git` |
| **HF Remote** | Hugging Face Spaces | `https://huggingface.co/spaces/apextrade-core/trade-ai-backend` |

* **Quant Server Boot Handshake**: `IntroSplash.jsx` automatically queries `/api/health` with live latency display. If local (`127.0.0.1` or `localhost`), it targets port `7860`; if online, it connects to Hugging Face Spaces. An offline bypass button (`Launch Terminal →`) is always available.
* **CORS Policy** (corrected 2026-10-30, code wins): `fc8f26a` REMOVED `allow_origin_regex` — CORS is now **allow-list only** (`allow_origins` in `app/main.py`): `localhost/127.0.0.1:5173|3000`, `https://trade-ai-beta.vercel.app`, `https://frontend-two-tau-82.vercel.app`, the HF Space URL, overridable via `ALLOWED_ORIGINS`. Local dev servers on OTHER ports (e.g. `vite preview` on 4173) get `400 Disallowed CORS origin` on preflight — serve local builds on 5173/3000 or extend the list.

---

## 4. 🔐 AUTH ROUTES & GATE BEHAVIOUR

| Route | Method | Auth | Description |
|-------|--------|------|-------------|
| `/api/login` | POST | **Public** | Single-code login (`username="code"`), returns JWT + sets `apt_token` cookie |
| `/api/auth/verify` | GET | **Cookie/Header** | Validates token, returns `{status: "valid"}` |
| `/api/logout` | POST | **Cookie/Header + CSRF** | Clears `apt_token` cookie (`CsrfDep` since `3cd877b`; `/api/login` stays exempt as session lifecycle) |
| `/api/health` | GET | **Public** | Health checks, startup handshake, latency |
| `/api/` | GET | **Protected** | Root status (requires `SessionDep`) |
| `/api/market_brief` | GET | **Protected** | Daily Market Briefing (`SessionDep`, rate-limited); feeds numbers only from the live signal-scan pipeline with a hard 10s backend timeout; on empty feeds/timeout returns HTTP **200** with `status: "unavailable"` + honest message — never invented values (`1cdd3c4`) |
| `/api/prices` | GET | **Public** | Simulated tick frame (`simulated: true`, `data_source: "SIMULATED"`) |
| `/ws/prices` | WS | **Public** | Simulated ticks (each tick carries `simulated: true`) |
| `/ws/bot` | WS | **Token** | Bot stream; requires `?token=` (close codes 4001/1008 stop reconnect) |
| `/api/quote` | GET | **Protected** | Single symbol quote (requires `SessionDep`) |
| `/api/history` | GET | **Protected** | Historical bars (requires `SessionDep`); MultiIndex columns flattened guard; when no bars are producible from any source it returns **503 with a retryable error** instead of a stale 404, and the response carries `data_source` (`angelone`/`yfinance`/`last-good`/`synthetic`) (`1cdd3c4`) |
| `/api/search` | GET | **Protected** | Symbol search (requires `SessionDep`) |
| `/api/keepalive` | GET | **Protected** | Keep-alive handshake (requires `SessionDep`) |
| `/api/chat/chart` | POST | **Protected** | Multimodal chart analysis (JSON, requires `SessionDep`) |
| `/api/chat/chart/upload` | POST | **Protected** | Multimodal chart analysis (multipart upload, requires `SessionDep`) |
| `/api/backtest/run` | POST | **Protected** | Historical backtest (requires `SessionDep`) |
| `/api/backtest/tournament` | POST | **Protected** | Tournament backtest (requires `SessionDep`, rate-limited 5/min) |
| `/api/strategies*` | * | **Protected** | Strategy list/detail/create (requires `SessionDep`); list reads the real DB store (`data_source: "db"`, presets-only fallback labelled `"presets"`), honours `active_only` |
| `/api/allocate` | POST | **Protected** | Portfolio allocation (requires `SessionDep`) |
| `/api/bot/*` | * | **Protected** | Bot control/status/trades (requires `TraderDep`/`AdminClearanceDep`) |
| `/api/signals*` | * | **Protected** | Signal scanning (requires `SessionDep`) |
| `/api/predictions*` | * | **Protected** | Predictions CRUD (requires `SessionDep`/`TraderDep`) |
| `/api/journal*` | * | **Protected** | Trade journal (requires `SessionDep`) |
| `/api/broker*` | * | **Protected** | AngelOne login/status (requires `TraderDep`) |
| `/api/admin/*` | * | **Admin** | Admin endpoints (requires `AdminDep`) |

> **Auth failure reality** (re-verified 2026-10-30, suite `296 passed` after TAR-21 test-harness alignment): a missing/invalid token is always `401` — **never `422`**; valid token → `200`. No `response_model` on `/api/auth/verify`; only explicit `401` or `200`. NOTE: `/api/auth/verify` is rate-limited **5/minute** (`RATE_LIMIT_AUTH`) — the 6th call inside a minute returns `429`, which the frontend treats as "not verified" and shows the code screen (token retained, no bypass). `csrf_protect` is **unconditional** since `fc8f26a` (the `TESTING=1` bypass is gone): every mutating route returns `403 {"detail":"CSRF token required"}` without `X-Requested-With` — live-probed on the Space. Exemptions: `/api/login` (session lifecycle) and `/api/admin/*` (scalar `X-Admin-Key` header). Rate limits: login/verify/logout 5/min, broker 3/min, signals-scan 15/min, chat 30/min, public routes 30/min, user routes 60/min, tournament 5/min, allocate 10/min; `/api/backtest/run` has **no explicit limiter** (global 120/min default only). `/api/quote` and `/api/backtest/run` exist ONLY in the v1 routers — main.py shadow duplicates were removed (`7a391e3`).

**Frontend Gate Logic (`App.jsx` + `api.js`):**
1. Mount → `verifyToken()` → `GET /api/auth/verify`
2. If 200 → `verified=true`, render workstation
3. If 401/no token → show `CodeEntryScreen`
4. User submits code → `POST /api/login` → sets `apt_token` cookie + `localStorage`
5. On any `apiFetch` 401 → clear tokens, dispatch `apex:auth-required` → show `CodeEntryScreen`

**CodeEntryScreen (`components/CodeEntryScreen.jsx`):**
- Clean dark only: `#0b0e13` background, `#12161d` card, `#1e2430` border
- Lucide icons: `Lock`, `AlertCircle`, `Eye`/`EyeOff`, `Loader2`
- Show/hide code toggle, monospace input, no signup/forgot links, no roles list

---

## 5. 💻 FRONTEND MODULE INVENTORY (`frontend/src/`)

### Core Views & Layout
* **`App.jsx`**: Main router, auth gate (`verifyToken`), layout scaffold, global shortcuts (`Ctrl+K`), state orchestration. Renders `CodeEntryScreen` when unauthenticated. `loggedIn = true` for personal workstation mode. `backendReady` flow fixed so a returning authenticated user boots straight into the workstation (`950e483`); briefing fetch carries an 18s AbortController timeout; backtest POST routed through `apiFetch`.
* **`IntroSplash.jsx`**: Cold-start quant server probe, health metrics checklist, latency counter, target URL switchers (Local 7860 / HuggingFace / Custom), offline fallback. Recognizes both `127.0.0.1` and `localhost` as local.
* **`main.jsx`**: React root with `ErrorBoundary` that renders "Try Again" button (accent-colored, resets crashed state) instead of raw stack traces. Reticle dev import removed.
* **`theme.js`**: Deep institutional dark palette tokens (`T.bg: #07090e`, `T.surface: #0d111a`, `T.accent: #6366f1`, `T.green: #00f5a0`, `T.red: #ff3366`). Unified `en-IN` formatting: `fmt()`, `fmtINR()`, `fmtPct()`, `fmtIST()`, `fmtISTDate()`, `fmtISTShort()` — all `Asia/Kolkata`. `SEED_PRICES` single source (deduplicated). Secondary tabs: `STRATEGIES`, `SETTINGS`, `HELP`.
* **`api.js`**: Dynamic base URL resolver, `apiFetch` (auth headers, 401 handler with token clearing + `apex:auth-required` dispatch), `verifyToken()`, `WS_BASE_URL` builder.

### Components
* **`components/Header.jsx`**: Institutional header with Lucide SVG navigation pills, active NSE market beacon (IST clock), latency badge, `Ctrl+K` search pill.
* **`components/CommandPalette.jsx`**: Global quick-actions drawer for instant symbol switching, tab navigation, emergency bot stop.
* **`components/CandleChart.jsx`**: TradingView Lightweight Charts canvas with timeframe selector (`1D` to `ALL`) and `📸 AI SCAN CHART` multimodal button. Loading/error state resets on symbol change; errors are HTTP-status-distinguished (not a generic offline message) with a RETRY control (`950e483`).
* **`components/ChatPanel.jsx`**: Gemini copilot chat with 1-click prompt chips (*Scan Breakouts, Support & Resistance, Regime*) and visual confidence gauge.
* **`components/CodeEntryScreen.jsx`** *(NEW)*: Single-code entry gate (flat dark, Lucide icons, show/hide toggle, `onVerified` callback).
* **`components/LandingPage.jsx`** *(NEW)*: Public landing hero with features grid, radial gradient backgrounds, floating animation keyframes.
* **`components/TermsPage.jsx`** *(NEW)*: Terms of service legal page.
* **`components/PrivacyPage.jsx`** *(NEW)*: Privacy policy legal page.
* **`components/DisclaimerPage.jsx`** *(NEW)*: Risk disclaimer with prominent warnings.
* **`components/WatchlistPanel.jsx`**: Real-time ticker cards with tick-up / tick-down animations.
* **`components/TickerBar.jsx`**: Marquee-style price ticker with `SIM` badge for HTTP-fallback data.
* **`components/OrderPanel.jsx`**: Order entry with MARKET/LIMIT toggle; validates limit price (empty = inline error, not silent failure).
* **`components/SystemHealthModal.jsx`**: Health diagnostics modal triggered from header beacon.
* **`components/BottomConsole.jsx`**: Positions / Orders / Alerts / AI tabs with embedded AI analyst.
* **`utils/apiErrors.js`** *(NEW, `950e483`)*: Shared error-shaping helpers (HTTP status → user-honest message) used by Home/Scanner/Chart panels; covered by `utils/apiErrors.test.js`. HomePanel shows the real briefing error state and RETRY is never disabled while loading; ScannerPanel uses a 90s timeout and banners that distinguish timeout vs filtered-empty vs error with the scanned count.

### Panels
* **`BotControlPanel.jsx`**: Autonomous bot controls, strategy selection, paper/live toggle, emergency square-off.
* **`AccountPanel.jsx`**: Institutional security terminal displaying `LEVEL_4_ROOT` clearance, session tokens, Angel One broker setup.
* **`PerformancePanel.jsx`**: Analytics panel — **removed hardcoded placeholders** (124 trades / 68.5% win rate). Now starts with `stats = null`, shows actionable empty states ("Log a prediction", "Resolve predictions") when no data, `source` badge (LIVE/SIMULATED/ERROR) always visible. Imports `T` from shared theme.
* **`BacktestRunner.jsx`**: Backtest/tournament runner — **fixed `{}` raw output** by checking `tournamentResults.leaderboard?.length` before rendering. Rate-limit hint on 429 (`5/min`).
* **`BrokerSettings.jsx`**: Show/hide toggle for sensitive fields (API Key, PIN, TOTP), masked inputs, Fernet encryption flow.

### Hooks
* **`hooks/useMarketData.js`**: Unified price source hook — imports `SEED_PRICES` from `theme.js` (single source of truth), returns `dataSource` map to distinguish WS from HTTP fallback.
* **`hooks/useHealthCheck.js`**: Health polling hook for IntroSplash.

---

## 6. ⚙️ BACKEND MODULE INVENTORY (`backend/app/`)

* **`main.py`**: FastAPI entrypoint, lifespan startup, CORS **allow-list only** (no regex since `fc8f26a` — see §3), route mounting. Generic `Exception` handler returns an internal-free body with `correlation_id` (`X-Correlation-ID` middleware + JSON logging); docs/redoc/openapi served only outside production (live-probed: `/docs` → 404 on the Space); dead shadow `/api/quote` + `/api/backtest/run` route duplicates removed (`7a391e3`).
* **`core/config.py`**: Pydantic v2 settings, v6.1.1. Production guards (`7a391e3`): invalid `FERNET_KEYS` **raise** in production/staging (never silently regenerate), `DEBUG=True` outside development raises, `DATABASE_URL` without explicit `ENVIRONMENT` raises, `PASS_ADMIN`/`APP_PASSWORD`/`JWT_SECRET`/`ADMIN_KEY` guard unchanged, and `live_trading_armed` is refused until the SEBI 2025 algo-trading compliance review — never weakened for Phase 1 paper runs.
* **`core/security.py`**: JWT create/decode, bcrypt, Fernet, `UserRegistry` (produces `RuntimeError` in production if the access code is missing — mirrors the Fernet raise with `settings.environment`), `require_session`/`optional_session`/`require_clearance` deps, CSRF (`CsrfDep` → `csrf_protect` requires `X-Requested-With` on **mutating routes only** — every session-gated POST/PUT/PATCH/DELETE, 403 otherwise; **unconditional since `fc8f26a`: the `TESTING=1` bypass was removed**, tests now send the same header the frontend's `apiFetch` always sends; never on GETs), `require_admin` (custom `X-Admin-Key` header = CSRF-immune). Default fallback clearance: `LEVEL_4_ROOT`. CSRF exemptions: `POST /api/login` only (session lifecycle); `/api/admin/*` uses the scalar key header. `POST /api/logout` carries `CsrfDep` (`3cd877b`).
* **`core/database.py`**: SQLAlchemy engine/session (PostgreSQL/SQLite). A non-empty `DATABASE_URL` is attempted as Postgres first (connection errors fall back); any non-empty URL that is not Postgres fails engine construction loudly — leave `DATABASE_URL` unset for the sanctioned sqlite fallback (the CI gate runs without it).
* **`api/v1/health.py`**: `/api/health` diagnostic + `/health/ping` + `/ready`. Truthful statuses (`7a391e3`): off workers report `disabled` (never "healthy" when never started), missing storage dirs are `warning` not a degraded driver, broker reports `paper_no_broker` (informational; paper mode needs no broker) vs `not_configured`, an explicit AI/status section is exposed, and paths/masked client code/DB error text are dropped from the public body.
* **`api/v1/auth.py`**: `/login` (code, CSRF-exempt session lifecycle), `/auth/verify`, `/logout` (now `CsrfDep`).
* **`api/v1/chat.py`**: `/chat`, `/chat/chart` (base64 JSON), `/chat/chart/upload` (multipart) — all `SessionDep`. When Gemini is unconfigured or errors, `/chat` falls back to a **deterministic heuristic reply** labelled `source: "heuristic"` — never presented as model/AI output (`8c74339`).
* **`api/v1/briefing.py`** *(NEW, `1cdd3c4`)*: `GET /api/market_brief` — composes the Daily Briefing strictly from the live signal-scan pipeline (breadth above EMA21, BUY-type setup %, top-confidence picks); hard 10s timeout; unavailable feeds → HTTP 200 `status: "unavailable"` with honest text; `risk_events` stays `[]` because no macro calendar source exists.
* **`api/v1/quotes.py`**: `/prices` (public), `/quote`, `/history`, `/search`, `/keepalive` — latter four `SessionDep`. `/history` uses the sourced download chain and responds with `data_source` (angelone / yfinance / last-good / synthetic); when no bars are producible it returns **503 retryable** (`1cdd3c4`).
* **`api/v1/bot.py`**: Start/pause/stop/status/trades — `TraderDep`/`AdminClearanceDep`; mutating routes carry `CsrfDep`, GET status/trades read freely. Paper-only: `paper=false` / `order_mode="live"` rejected with 400. Trades log statuses include `SQUARE_OFF`.
* **`api/v1/predictions.py`**: CRUD + stats — `SessionDep`/`TraderDep`. `DELETE /api/predictions/{id}` is **session-user-scoped** (`3990879`): deleting another user's prediction returns `404` — no existence leak. Manual resolve persists PnL/R/holding and tags `NOT_MEASURED` explicitly when not measured (`80e9af2`).
* **`api/v1/signals.py`**: Scan endpoints — `SessionDep`. `/api/signals` + `/api/scan` responses include a **`gates` breakdown** of per-symbol gate rejections (`84e6215`) and tag each result with `data_source`.
* **`api/v1/broker.py`**: AngelOne login/status — `TraderDep`; encrypted Fernet persistence.
* **`api/v1/backtest.py` / `tournament.py` / `allocate.py` / `strategies.py` / `admin.py`**: `SessionDep`/clearance-guarded; mutating routes carry `CsrfDep`; strategy list reads the real DB store (`data_source: "db"` with honest `"presets"` fallback).
* **`trading_agent.py`**: Autonomous signal generation, risk management, order routing loops. **Phase 1 paper-only** (docstring + `order_mode="paper"` payload writes; live arming refused). Covers the 3:20 PM IST auto square-off (`_square_off_all`): BUY/SELL move math against a live quote, `pnl_inr = price_move × position_size`, computed `r_multiple` and holding minutes, `status="SQUARE_OFF"` + `resolution_reason="SQUARE_OFF_3_20"`, rows without a live quote stay pending for the next cycle, one bad row never blocks the others (`80e9af2`); failed prediction inserts are logged as failures, not swallowed.

---

## 7. 🧪 TEST INFRASTRUCTURE (`backend/tests/`)

* **`conftest.py`**: `auth_client` fixture creates a TestClient with a valid `apt_token` cookie **and the `X-Requested-With` header the real frontend always sends** (CSRF is unconditional since `fc8f26a`; tests asserting the missing-header 403 keep bare clients).
* **Backend suite**: **296 passed / 0 failed** (re-run 2026-10-30 at lineage `2d22822`; TAR-21 follow-up `69dca49` aligned 11 test clients with the unconditional CSRF — before that alignment the suite was 255/41 at HEAD `fc8f26a` because 41 tests predated the bypass removal).
* **Frontend**: **46 passed** vitest tests across 9 files — `src/api.test.js` (FormData uploads, auth headers), `utils/apiErrors.test.js` (status-distinguished errors), `utils/briefing.test.js`; `npm run build` 0 errors (~2.4s, 1822 modules).

---

## 8. 🤖 EXTENSIONS & AUTOMATION AGENTS

### 1. Google Artemis (`google/artemis`)
* **Local Repo**: `c:\Users\aryan\OneDrive\Desktop\main app\artemis`
* **Active Device**: `emulator-5554` (BlueStacks 5 Android Emulator running on `127.0.0.1:5555`)
* **Status**: **ONLINE & VERIFIED** (5/5 checks pass, visual screenshot & element grounding active).
* **LLM Engine**: NVIDIA Nemotron (`nvidia/llama-3.1-nemotron-70b-instruct`) via OpenAI-compatible endpoint.
* **MCP Tools**: `mobile_run_task`, `mobile_get_device_state`, `mobile_inspect_trace`, `mobile_diagnose`.

### 2. Google Agents CLI (`google/agents-cli`)
* **Version**: `1.11.0` (installed globally via `uv tool install`)
* **Skills Active (7/7)**: Workflow, ADK code, scaffold, eval, deploy, publish, observability.

---

## 9. 🧪 QUALITY GATES & VERIFICATION COMMANDS

```bash
# 1. Frontend Build Verification (clean, 0 errors in ~1.7s)
cd frontend
npx vite build

# 2. Backend Test Suite (285 passing)
cd ..
.venv\Scripts\python.exe -m pytest backend/tests/ -q

# 3. Artemis Device Diagnosis
# In IDE: Call MCP tool mobile_diagnose() -> Verdict: ready / degraded
```

### Repair Pass Results (2026-10-26, v6.1.0)

* **Backend**: `233 passed` (`pytest`, 57 warnings, 15.26s).
* **Frontend**: `3 test files / 12 tests passed` (`vitest`), `npm run build` succeeded (1816 modules, 1.78s).
* **Bot WS**: token appended as `?token=`, auth close codes `4001`/`1008` stop reconnect, exponential backoff 3s->30s.
* **Paper only**: `POST /api/bot/start` rejects `paper=false` / `order_mode="live"` with 400; payload writes `order_mode="paper"`.
* **Simulated data**: `/api/prices` and `/ws/prices` emit `simulated: true`; LandingPage copy no longer claims real-time NSE data.
* **Honest metrics**: `/api/data/confidence` returns null/`NOT_MEASURED` without a quality record; admin simulation returns no fabricated metrics; worker status reads broker feed auth state.
* **DB path**: legacy `db.py` and `app/core/database.py` both resolve `trading_platform.db` at repo root; unused plaintext broker-session repository removed.
* **CI**: `c9372bc` grew the ci.yml pytest list 13 → 15 files (added `test_csrf`, `test_t15_security`); still not all 41 backend test files run in CI — full pytest remains the release gate.

### Docs Sync Verification (2026-10-27, v6.1.0 — TAR-19, HEAD `8c74339`)

* **Backend**: `262 passed, 0 failed` (pytest; CI gate runs 15 test files in `ci.yml`).
* **Frontend**: `npm run build` 0 errors; `vitest` 36/36 passed.
* **Live auth probes**: `GET /api/auth/verify` without/with bad token → `401`/`401` (never `422`).
* **Known lint debt**: `npm run lint` still reports pre-existing errors in untouched components; build and tests are clean.

---

## 10. 📝 CHANGELOG — v4.1.0 (2026-10-25)

### P0: TickerBar Crash Fix
**Root cause**: `App.jsx` used `<TickerBar>`, `<BottomConsole>`, `<WatchlistPanel>`, and `<OrderPanel>` in JSX but none were imported. During the v5 refactor, imports were not preserved when components were extracted, causing `ReferenceError: TickerBar is not defined` at runtime when `verified=true`.

**Fix**: Added proper imports in `App.jsx`:
```javascript
import TickerBar from './components/TickerBar';
import BottomConsole from './components/BottomConsole';
import WatchlistPanel from './components/WatchlistPanel';
import OrderPanel from './components/OrderPanel';
```

**Verification**: `npm run build` passes with 0 errors; fresh profile load renders workstation correctly.

---

## 11. 📝 CHANGELOG — v4.2.0 (2026-10-25)
### P0: /api/auth/verify 422 Fix
**Root cause**: `verify` endpoint in `backend/app/api/v1/auth.py` used `response_model=StatusResponse`. While FastAPI typically returns 401 when the dependency logic raises HTTPException, the `response_model` can cause unexpected 422 responses during response validation in some deployments.

**Fix**: Removed `response_model=StatusResponse` from the verify endpoint, ensuring only explicit `401` (invalid/no token) or `200` (valid token) responses are returned.

**Verification**: GET `/api/auth/verify` without token → `401`; with valid token → `200`.

---

## 12. 📝 CHANGELOG — v5.0.0 (2026-10-25) — OpenCode v6 Direction
### New Components
* **`CodeEntryScreen.jsx`** — Standalone single-code auth gate component (extracted from monolithic App.jsx). Flat dark design, Lucide icons, `onVerified` callback.
* **`LandingPage.jsx`** — Public-facing landing page with hero section, feature cards, radial gradient ambient effects, floating animations.
* **`TermsPage.jsx`** — Terms of service legal page.
* **`PrivacyPage.jsx`** — Privacy policy page.
* **`DisclaimerPage.jsx`** — Risk disclaimer page with prominent financial risk warnings.

### Auth & Security
* **`api.js`**: Added `verifyToken()` function. `apiFetch` 401 handler now clears `sessionStorage`/`localStorage` tokens and dispatches `apex:auth-required` custom event.
* **`security.py`**: Production-mode `RuntimeError` if `PASS_ADMIN`/`APP_PASSWORD` unset (environment detection via `ENVIRONMENT` env var).
* **`config.py`**: Additional production environment validation.

### Route Auth Upgrades
* **`tournament.py`** and `allocate.py` upgraded from `OptionalSessionDep` to `SessionDep`.

### Crash Recovery (P0-2)
* **`main.jsx`**: ErrorBoundary replaced raw `<pre>` stack trace with clean crash message + accent-colored "Try Again" button that resets state. Removed dead Reticle dev import.

### Analytics Fix (P0-3)
* **`PerformancePanel.jsx`**: Removed hardcoded placeholder stats (`124 trades`, `68.5% win rate`). Stats initialized to `null`. Empty state shows actionable buttons ("Log a prediction", "Resolve predictions"). Source badge (LIVE/SIMULATED/ERROR) always visible. Imports shared `T` from `theme.js` instead of local duplicate.

### Other Changes
* **`IntroSplash.jsx`**: Refinements to connection flow.
* **`Header.jsx`**: Minor styling updates.
* **`TickerBar.jsx`**: SIM badge for HTTP-fallback prices.
* **`TextInput.jsx`**: Component updates.
* **`useMarketData.js`**: Unified price source, `dataSource` map.
* **`App.jsx`**: Major refactor — 1536+ lines of deletion. Extracted auth, landing, legal pages into standalone components.

### Repair Pass Results (2026-10-26, v6.1.0)

* **Backend**: `233 passed` (`pytest`, 57 warnings, 15.26s).
* **Frontend**: `3 test files / 12 tests passed` (`vitest`), `npm run build` succeeded (1816 modules, 1.78s).
* **Bot WS**: token appended as `?token=`, auth close codes `4001`/`1008` stop reconnect, exponential backoff 3s->30s.
* **Paper only**: `POST /api/bot/start` rejects `paper=false` / `order_mode="live"` with 400; payload writes `order_mode="paper"`.
* **Simulated data**: `/api/prices` and `/ws/prices` emit `simulated: true`; LandingPage copy no longer claims real-time NSE data.
* **Honest metrics**: `/api/data/confidence` returns null/`NOT_MEASURED` without a quality record; admin simulation returns no fabricated metrics; worker status reads broker feed auth state.
* **DB path**: legacy `db.py` and `app/core/database.py` both resolve `trading_platform.db` at repo root; unused plaintext broker-session repository removed.
* **CI**: `c9372bc` grew the ci.yml pytest list 13 → 15 files (added `test_csrf`, `test_t15_security`); still not all 41 backend test files run in CI — full pytest remains the release gate.

---

## 13. 📝 CHANGELOG — v6.0.0 (2026-10-25) — Live Regression Fix
### P0: TickerBar Crash Fix
**Root cause**: `App.jsx` used `<TickerBar>`, `<BottomConsole>`, `<WatchlistPanel>`, and `<OrderPanel>` in JSX but none were imported. During the v5 refactor, imports were not preserved when components were extracted, causing `ReferenceError: TickerBar is not defined` at runtime when `verified=true`.

**Fix**: Added proper imports in `App.jsx`:
```javascript
import TickerBar from './components/TickerBar';
import BottomConsole from './components/BottomConsole';
import WatchlistPanel from './components/WatchlistPanel';
import OrderPanel from './components/OrderPanel';
```

**Verification**: `npm run build` passes with 0 errors; fresh profile load renders workstation correctly.

---

## 14. 📝 CHANGELOG — v6.1.0 (2026-10-27) — Production-Ready Pass
Fixes landed on main at HEAD `80e9af2` (lineage `e5bcccf..80e9af2`; backend suite **285 passed / 0 failed**, frontend **46 vitest / build 0 errors** — per-commit attested: `3cd877b` 262, `1cdd3c4` 272, `7a391e3` 253-in-lane, `80e9af2` 278, live re-run 2026-10-28 = 285):

* **Bot loop truth** (`3cd877b`): prediction payloads always carry `prediction_type` (+ `macd_hist`, `position_size`, `vwap_dist` where computed); Phase-1 paper docstring; failed prediction inserts are logged as failures, not swallowed.
* **CSRF completion** (`3cd877b`): `CsrfDep` on `POST /api/logout`, admin `DELETE /api/admin/signals/clear` + `POST /api/admin/run-simulation`; login exemption documented.
* **Briefing route** (`1cdd3c4`): `GET /api/market_brief` from the live scan pipeline, 10s timeout, honest 200-unavailable, never invented numbers.
* **History honesty** (`1cdd3c4`): `data_source` tagging (angelone/yfinance/last-good/synthetic), MultiIndex flatten guard, `503 retryable` when nothing is producible.
* **Production hardening** (`7a391e3`): config guards (Fernet raise, DEBUG gate, DATABASE_URL+ENVIRONMENT, `live_trading_armed` SEBI gate, version 6.1.1), truthful health statuses, generic 500 + correlation id, docs off in production, shadow routes removed.
* **Square-off reality** (`80e9af2`): 3:20 PM square-off computes real `pnl_inr = price_move × position_size`, `r_multiple`, holding minutes; distinct `SQUARE_OFF` status + `SQUARE_OFF_3_20` reason; `position_size` stored end-to-end; manual resolve persists PnL/R/holding with explicit `NOT_MEASURED` labels.
* **Frontend resilience** (`950e483`): returning-user `backendReady` fix, 18s briefing timeout, status-distinguished errors + RETRY on Home/Chart/Scanner, backtest through `apiFetch`, 90s scanner banner.
* **CI** (`a6d09f4`): pytest gate expanded **15 → 24 test files**, broken `DATABASE_URL: sqlite:///:memory:` gate env var removed (it crashed SQLAlchemy 2.x collection), and a new **root-Dockerfile build + `/api/health/ping` smoke job**. The gate remains a 24-of-48 subset; full pytest stays the release gate.
* **Version reality**: backend `6.1.1` (`config.py`); frontend `package.json` remains `6.1.0` pending the Task-13-frontend chip bump (not landed as of HEAD `80e9af2`).

---

## 10a. 📝 CHANGELOG — v6.1.1 (2026-10-29/30) — TAR-20/21 Security Passes

* **TAR-20 persistence** (`34fa14e`, owner): `data_source` + journal target/stop persist to DB; frontend keys accepted by JournalEntry/PredictionCreate schemas (296 pass at commit time).
* **TAR-21 Security Lead fixes** (`fc8f26a`, owner): `csrf_protect` made **unconditional** (the `TESTING=1` bypass removed — mutating routes always require `X-Requested-With`); `allow_origin_regex` **removed** from both `backend/app/main.py` and root `main.py` (CORS = explicit allow-list only); root `main.py` no longer falls back to loading `.env.example` placeholders.

---

## 10b. 📝 CHANGELOG — 2026-10-30 — Learn/Verify/Deploy Run (this session)

**Verification (all re-run at lineage `2d22822`):**
* Backend pytest: **296 passed / 0 failed** (after `69dca49` test-harness alignment; 255/41 at bare `fc8f26a` — every failure was `403 CSRF token required` from tests predating the bypass removal).
* Frontend: `npm run build` 0 errors (1822 modules); vitest **46/46**.
* `/api/auth/verify`: no token → `401`, invalid token → `401`, valid (local test) token → `200 {status: "valid"}` — never `422`. Local + live probes both.
* Production-build runtime check (fresh browser profile): unauthenticated load → flat-dark CodeEntryScreen only; login with **locally invented test code** → terminal renders, TickerBar shows live SIM-labelled ticks, `errors: []`; **3/3 spaced reloads** no crash, session persists. (Note: 3 rapid unspaced reloads can trip the 5/min verify limit → honest code-screen fallback, token retained.)
* ErrorBoundary "Try Again": triggered via test-only crash build (trigger removed after; clean rebuild byte-identical). Unauthenticated crash → Try Again → code screen, no loop, no bypass; authenticated crash → Try Again → verifyToken 200 → terminal. No stack traces in UI.
* Theme token grep: `T.gold` / `T.yellow` / `T.blueDim` / `T.blueGlow` → **0 references** (panels define local palette constants or inline values).
* Broker Fernet: `POST /api/angelone/login` → `save_angelone_session` encrypts api_key/pin/totp/tokens via Fernet MultiFernet before SQLite persistence (`db.py::_encrypt_field` → `app.core.security.encrypt_value`); failure to encrypt raises (never stores plaintext).

**Deploy:**
* Backend → **HF Space LIVE**: push rejected by xet pre-receive (binary `palace/` ChromaDB files) → `palace/` untracked + gitignored (`2d22822`, no runtime impact — image copies `backend/` only) → deploy commit `adbcf9c` (single-tree squash onto Space tip `5256014`). First boot hit **RUNTIME_ERROR**: `DATABASE_URL` set but `ENVIRONMENT` unset (7a391e3 guard — the guard worked as designed). **Fix: Space variable `ENVIRONMENT=production` set 2026-10-30 → RUNNING.** Live probes: `/api/health` = `6.1.1 / production / degraded` (degraded = AI services unconfigured — honest), verify `401`/`401`, CSRF `403` without header, `/docs` `404`.
* Frontend → **Vercel already current**: `git push origin main` (`fc8f26a..2d22822`); Vercel CLI is logged out and no Git-integration deploy fired, but the live bundle `index-B-kdwbPu.js` is **byte-identical** to a fresh local build of current source with Vercel's env (frontend untouched by this run) — confirmed live + via-replica build. Live incognito probes: code screen only, no terminal/admin leak, `errors: []`, **3/3 reloads** clean; verify via Vercel proxy `401`/`401`.

**Doc-vs-code discrepancies found this run (code wins):**
1. `LandingPage/TermsPage/PrivacyPage/DisclaimerPage` exist but are **imported nowhere** — no route renders them; they cannot be opened from the live site.
2. Obsidian `Home.md` claimed v6.1.0 / 262 tests / `TAR-19` as latest — stale (backend was 6.1.1, suite 296).
3. §10 of the older doc claimed frontend `package.json` 6.1.0 — actual: 6.1.1.
4. CORS docs claimed regex `localhost:*`/`*.vercel.app` — actual since `fc8f26a`: allow-list only.
5. HF Space had been running with `ENVIRONMENT` unset (default-development) — surfaced by the 7a391e3 boot guard on this deploy; now explicit `production`.

**Owner-tested (not verified by this run):** the live correct-access-code → terminal step on `https://trade-ai-beta.vercel.app/` (this run never used, requested, or committed the owner's live code).
