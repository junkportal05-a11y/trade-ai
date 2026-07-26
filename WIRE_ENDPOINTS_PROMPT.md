# ApexTrade — Wire Remaining Backend↔Frontend Endpoints Prompt

> **Context**: ApexTrade is a FastAPI + React trading terminal. The backend is at `backend/`, frontend at `frontend/`. The app deploys to HuggingFace Spaces (backend) and Vercel (frontend). After completing, commit all changes and push to both `origin main` and `huggingface main`.

---

## ✅ Already Done (DO NOT redo these)

1. **`POST /api/predictions/{id}/resolve`** — Endpoint exists in `backend/app/api/v1/predictions.py`. Schema `PredictionResolveRequest` exists in `backend/app/models/schemas.py`.
2. **`GET /api/data/confidence`** — Endpoint exists in `backend/app/api/v1/signals.py`. Returns `overall_confidence`, `freshness_status`, `scores[]`.
3. **`toFix()` crash guard** — Frontend `.toFixed()` calls in `PredictionsPanel.jsx` and `PerformancePanel.jsx` guarded with nullish coalescing.

---

## 🔧 Task 1: Fix `POST /api/backtest/run` — HTTP Method & Route Mismatch

### Problem
- The frontend (`BacktestRunner.jsx` line 57, `SimulatorPanel.jsx` line 45) sends **`POST /api/backtest/run`** with a JSON body.
- The backend has the endpoint at **`GET /api/backtest/run`** in `backend/app/main.py:106` using query params via `Depends()`.
- There is also a **dead duplicate** at `POST /api/backtest` in `backend/app/api/v1/backtest.py` that calls a stub service.

### What to do
1. In `backend/app/main.py:106`, change `@app.get("/api/backtest/run")` → `@app.post("/api/backtest/run")`.
2. Change the function signature to parse a JSON body instead of query params:
   - Accept `Request` and use `body = await request.json()`.
   - OR change to `backtest: BacktestRequest` (FastAPI auto-parses JSON body for POST).
3. The `BacktestRequest` schema in `backend/app/models/schemas.py:261` requires ALL fields (`risk_pct`, `stop_atr`, `target_atr`, `initial_capital`, `entry_score`, `adx_min`) but the frontend only sends `{ symbol, start_date, end_date, strategy, capital, stop_atr }`. **Add sensible defaults** so the frontend doesn't get 422 errors:
   ```python
   risk_pct: float = Field(default=2.0, gt=0)
   stop_atr: float = Field(default=1.5, gt=0)
   target_atr: float = Field(default=2.0, gt=0)
   initial_capital: float = Field(default=100000, gt=0)
   entry_score: int = Field(default=60, ge=0)
   adx_min: float = Field(default=20, ge=0)
   ```
4. Also add a `strategy: str | None = None` and `capital: float | None = None` field to `BacktestRequest` since the frontend sends those. If `capital` is provided, use it as `initial_capital`.
5. Remove the dead duplicate at `backend/app/api/v1/backtest.py` (or redirect it to the main.py endpoint).
6. **Test**: Submit a backtest from the UI in `BacktestRunner.jsx` and confirm metrics come back.

### Frontend sends (reference)
```json
{
  "symbol": "RELIANCE.NS",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "strategy": "intraday_momentum",
  "capital": 100000,
  "stop_atr": 1.5
}
```

### Backend should return (reference)
```json
{
  "total_pnl_pct": 12.5,
  "max_drawdown": -8.2,
  "win_rate": 62.5,
  "profit_factor": 1.45,
  "total_trades": 48,
  "sharpe_ratio": 1.2,
  "final_capital": 112500
}
```

---

## 🔧 Task 2: Add `POST /api/admin/run-simulation` & `GET /api/admin/simulation-status`

### Problem
- `frontend/src/api.js:42` calls `POST /api/admin/run-simulation` with `{ start_date, end_date }` and header `x-admin-key`.
- `frontend/src/api.js:48` calls `GET /api/admin/simulation-status` with header `x-admin-key`.
- `frontend/src/SimulatorPanel.jsx` uses these (imported but currently falls back to `/api/backtest/run` directly).
- Neither endpoint exists in `backend/app/api/v1/admin.py`.

### What to do
1. In `backend/app/api/v1/admin.py`, add two new endpoints:

```python
@router.post("/run-simulation", response_model=dict)
async def run_simulation(
    request: Request,
    params: AdminKeyParams = Depends(),
) -> dict:
    require_admin(params.x_admin_key)
    body = await request.json()
    # Delegate to the same backtest engine used by /api/backtest/run
    # Use body.get("start_date"), body.get("end_date"), body.get("symbol", "NIFTY")
    # Return the same metrics dict
    ...

@router.get("/simulation-status", response_model=dict)
def simulation_status(
    params: AdminKeyParams = Depends(),
) -> dict:
    require_admin(params.x_admin_key)
    # Since backtests run synchronously, return a static "idle" status
    return {"status": "idle", "message": "No simulation running"}
```

2. Import `Request` from FastAPI in admin.py.
3. The `require_admin` function and `AdminKeyParams` schema already exist — reuse them.
4. **Test**: Call from SimulatorPanel UI.

---

## 🔧 Task 3: Wire Strategy Presets in `/api/strategies`

### Problem
- Frontend `StrategySelector.jsx:51` calls `GET /api/strategies` and expects:
  ```json
  {
    "strategies": [
      { "id": "intraday_momentum", "name": "Intraday Momentum", "description": "...", "riskProfile": "Moderate", "typicalHold": "15m-2h" },
      ...
    ]
  }
  ```
- Backend `backend/app/api/v1/strategies.py` returns a **flat list** `[{ "id": 1, "name": "..." }]` — no wrapper object, wrong shape, wrong data.

### What to do
1. Replace `MOCK_STRATEGIES` in `backend/app/api/v1/strategies.py` with strategy presets that match the frontend's `STRATEGY_PRESETS`:
```python
STRATEGY_PRESETS = [
    {"id": "intraday_momentum", "name": "Intraday Momentum", "description": "EMA crossover + RSI + volume filter. 15m timeframe.", "riskProfile": "Moderate", "typicalHold": "15m-2h"},
    {"id": "mean_reversion", "name": "Mean Reversion", "description": "Bollinger Band squeeze + RSI extremes. 5m-15m timeframe.", "riskProfile": "Low", "typicalHold": "5m-30m"},
    {"id": "breakout_volume", "name": "Breakout Volume", "description": "High volume breakout + ADX trend filter. 15m-1h timeframe.", "riskProfile": "High", "typicalHold": "30m-4h"},
    {"id": "scalper_rsi", "name": "RSI Scalper", "description": "Fast RSI extremes + EMA alignment. 1m-5m timeframe.", "riskProfile": "High", "typicalHold": "1m-10m"},
    {"id": "swing_trend", "name": "Swing Trend Follower", "description": "Daily EMA trend + weekly MACD. 1h-1d timeframe.", "riskProfile": "Low", "typicalHold": "1d-2w"},
]
```
2. Change the `GET ""` endpoint to return `{"strategies": STRATEGY_PRESETS}` (wrapped in an object, not a bare list).
3. **Test**: Verify `StrategySelector.jsx` loads and displays the strategies.

---

## 🔧 Task 4: Backend `/api/predictions/stats` Returns Incomplete Data

### Problem
The backend `GET /api/predictions/stats` (in `backend/app/api/v1/predictions.py`) only returns 3 fields:
```json
{"win_rate": 0.0, "avg_error": 0.0, "resolved_predictions": 0}
```
But the frontend `PredictionsPanel.jsx` expects ALL of these:
- `total_predictions`, `resolved_predictions`, `win_rate`, `avg_error`
- `profit_factor`, `empirical_rr_ratio`, `expected_value_pct`, `max_drawdown_pct`
- `best_sector`, `worst_sector`, `avg_confidence`, `recent_outcomes[]`, `leaderboard[]`

### What to do
Extend `get_prediction_stats()` in `backend/app/api/v1/predictions.py` to compute and return all fields the frontend needs. For fields that can't be computed yet (like leaderboard), return sensible defaults:
```python
return {
    "total_predictions": total,
    "resolved_predictions": n,
    "win_rate": round(wins / n * 100, 1) if n else 0.0,
    "avg_error": ...,
    "profit_factor": ...,      # sum of winning PnL / abs(sum of losing PnL), default 0.0
    "empirical_rr_ratio": ..., # avg win pnl / abs(avg loss pnl), default 0.0
    "expected_value_pct": ..., # (win_rate * avg_win) - ((1-win_rate) * avg_loss), default 0.0
    "max_drawdown_pct": 0.0,   # placeholder
    "best_sector": "N/A",
    "worst_sector": "N/A",
    "avg_confidence": ...,     # average confidence_score of all predictions
    "recent_outcomes": [],     # last 10 resolved predictions as mini dicts
    "leaderboard": [],         # empty for now
}
```

---

## Deployment

After all changes:
```bash
git add -A
git commit -m "feat: wire all remaining backend-frontend endpoints (backtest/run, admin/simulation, strategies, prediction stats)"
git push origin main
git push huggingface main
```

Then verify the HuggingFace Space rebuilds successfully by hitting `GET https://apextrade-core-trade-ai-backend.hf.space/` and confirming a 200 response.
