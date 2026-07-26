# ApexTrade — Backend to Frontend Unwired Endpoints TODO List

> **Status:** COMPLETED ✅  
> **Goal:** Connect and wire all 5 missing/mismatched API endpoints between FastAPI backend and React frontend.

---

## 📋 TODO Checklist

### 1. Implement `POST /api/predictions/{id}/resolve`
- [x] Add `PredictionResolveRequest` model in `backend/app/models/schemas.py`.
- [x] Add `@router.post("/predictions/{prediction_id}/resolve")` endpoint in `backend/app/api/v1/predictions.py`.
- [x] Calculate `pnl_pct` and update `resolved_at`, `status`, and `actual_outcome` in database via repository.
- [x] Test resolving a prediction from `PredictionsPanel.jsx`.

### 2. Implement `GET /api/data/confidence`
- [x] Add `@router.get("/data/confidence")` endpoint in `backend/app/api/v1/signals.py`.
- [x] Return data quality score (`confidence_score`, `freshness_status`, `symbol`).
- [x] Test fetching confidence scores in `PredictionsPanel.jsx`.

### 3. Fix `POST /api/backtest/run` HTTP Method & Payload Mismatch
- [x] Add `@router.post("/backtest/run")` in `backend/app/main.py` and `backend/app/api/v1/backtest.py`.
- [x] Accept JSON POST payload (`BacktestRequest` schema) with `symbol`, `start_date`, `end_date`, `initial_capital`, `risk_pct`.
- [x] Call `run_historical_backtest()` engine and return metrics dict (`win_rate`, `total_pnl_pct`, `sharpe_ratio`, `max_drawdown`).
- [x] Test submission from `BacktestRunner.jsx` and `SimulatorPanel.jsx`.

### 4. Implement `POST /api/admin/run-simulation` & `GET /api/admin/simulation-status`
- [x] Add `@router.post("/run-simulation")` and `@router.get("/simulation-status")` in `backend/app/api/v1/admin.py`.
- [x] Require `X-Admin-Key` header authentication via `AdminKeyParams`.
- [x] Return simulation execution status to support `api.js` helpers.

### 5. Wire Strategy Presets in `/api/strategies`
- [x] Update `backend/app/api/v1/strategies.py` to return standard strategy presets matching `STRATEGY_PRESETS` in `StrategySelector.jsx`.
- [x] Test strategy loading in `StrategySelector.jsx`.
