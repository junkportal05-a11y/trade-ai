# Trading AI Autonomous System - Technical Audit & Fix TODO List

> **Status:** Queued for execution by Claude Code.
> **Permission Directive:** Manual verification tasks (container/process/log checks, manual paper trade tracing) are marked as pre-approved manual actions. Code tasks remain queued in the todo list.

---

## 📋 Code Tasks (For Claude Code)

### [x] Task 1: Implement Missing n8n & Watchdog API Endpoints
- **Explanation:** 
  The n8n Kill Switch Monitor and Data Integrity Watchdog workflows expect specific REST endpoints that are currently missing in the backend:
  - `GET /api/n8n/kill-switch-check`
  - `GET /api/n8n/data-integrity-check`
  - `GET /api/n8n/metrics`
  - `POST /api/agent/trigger-scan`
  Furthermore, `GET /api/n8n/status` (in `app/main.py`) returns a schema mismatch (`status/degraded/workers` instead of `agent_running/market_open/angelone_authorized`).
- **Required Action:**
  Create and register these 4 endpoints in FastAPI with proper responses, and update `GET /api/n8n/status` payload structure so the n8n kill switch does not return 404 errors.

---

### [x] Task 2: Wire Up `trading_agent_loop()` Startup & Governance Worker
- **Explanation:**
  `trading_agent_loop()` is defined in the codebase but never launched during application startup (in `lifespan()` in `app/main.py`). `governance_worker.py` contains kill-switch logic but is not imported or executed anywhere.
- **Required Action:**
  Update `lifespan()` in `app/main.py` to launch `trading_agent_loop()` as an asynchronous background task (`asyncio.create_task`) during startup, and integrate/import `governance_worker.py` into the execution lifespan.

---

### [x] Task 3: Fix Deployment Entrypoint Path in Dockerfile and Procfile
- **Explanation:**
  Both `Dockerfile` (`CMD ["uvicorn", "main:app", ...]`) and `Procfile` (`web: uvicorn main:app ...`) reference `main:app` directly, but the main application file is located at `backend/app/main.py` (or `app/main.py` depending on context root).
- **Required Action:**
  Update `Dockerfile` and `Procfile` command strings to point accurately to `backend.app.main:app` or set `PYTHONPATH`/`WORKDIR` correctly so container startup does not fail.

---

### [x] Task 4: Implement `prediction_resolver_worker` for Intraday SL/TP Resolution
- **Explanation:**
  Comments in `trading_agent.py` state that `prediction_resolver_worker` regularly polls open trades against Stop Loss (SL) and Take Profit (TP) levels. However, `prediction_resolver_worker` is not implemented anywhere in the codebase. As a result, positions are only closed at 3:20 PM via `_square_off_all()`, tagging every trade with `status="TIMEOUT"` regardless of intraday price movements.
- **Required Action:**
  Create `prediction_resolver_worker` background polling logic to continually check active open trades against live/historical price targets (TP) and stop losses (SL), setting trade status appropriately to `TARGET_HIT` or `STOP_HIT`.

---

### [x] Task 5: Fix Type Mismatch in Manual Prediction Resolution (`PredictionsPanel.jsx` & Pydantic Schema)
- **Explanation:**
  `PredictionsPanel.jsx` sends `{ actual_outcome: parseFloat(actualOutcomeInput), status: ... }`, sending a `float` to the backend. The backend Pydantic schema `PredictionResolveRequest` (`app/models/schemas.py`) expects `actual_outcome` to be a string matching `^(TARGET_HIT|STOP_HIT|EXPIRED|MANUAL_EXIT)$`. This causes HTTP 422 Unprocessable Entity errors on manual UI resolution.
- **Required Action:**
  Align frontend state/payload in `PredictionsPanel.jsx` to send the string outcome enum (or update schema handling cleanly) so manual resolution passes Pydantic validation.

---

### [x] Task 6: Replace Fabricated Fields in `get_prediction_stats` with Dynamic Calculations
- **Explanation:**
  In `app/api/v1/predictions.py`, performance fields like `max_drawdown_pct` (4.5), `best_sector` ("IT"), `worst_sector` ("BANK"), and leaderboard entries ("EMABreakout") are hardcoded static values rather than calculated from actual resolved trades.
- **Required Action:**
  Compute `max_drawdown_pct`, `best_sector`, `worst_sector`, and strategy leaderboard metrics dynamically based on actual database records of resolved trades.

---

## 🛠️ Manual Verification & Inspection Tasks (Pre-Approved / No Permission Needed)

### [ ] Task M1: Verify Deployed Process & Container Status
- **Explanation:**
  Check the actual deployed process list (`ps aux` / Space boot logs) on HuggingFace Space or local container execution to verify whether `main:app` starts properly or crashes on boot, and whether `trading_agent_loop` emits log output.

### [ ] Task M2: End-to-End Paper Trade Verification
- **Explanation:**
  Place a manual paper trade for a single symbol and trace it end-to-end through the resolution pipeline to confirm whether trade status accurately transitions to `TARGET_HIT` / `STOP_HIT` versus defaulting to `TIMEOUT`.
