# Reconstructed Specification: ApexTrade Full Rebuild

## Slice Perimeter
Frontend (`frontend/src/`) and backend (`backend/`) code modified during the rebuild. 24 files, ~5,000 lines changed.

---

## 1. Behavioral Requirements (WHEN → THEN)

### Requirement R1: 5-Section Navigation
- **WHEN** user loads the app, **THEN** they see 5 navigation sections: Home, Charts, Scanner, Predictions, Strategies
- **Constraints**: Dark-only theme (`#080808` family), no trading/execution UI, no portfolio/P&L

### Requirement R2: Two Background Workers Only
- **WHEN** app starts, **THEN** two asyncio tasks are created:
  1. `prediction_loop` — runs strategies on schedule, records predictions
  2. `prediction_resolver_worker` — resolves SL/TP, updates accuracy per strategy
- **Legacy aliases**: `trading_agent_loop` → `prediction_loop` (for test compat)
- **No**: bot engine, order-placement, broker connections, real-money UI

### Requirement R3: Prediction Engine Form
- **WHEN** user opens Predictions section, **THEN** AI Prediction Engine form is present
- **Form fields**: symbol, prediction_type (BULLISH/BEARISH), entry_price, target_price, stop_loss, confidence_score
- **Action**: Submit → records prediction via `db.add_prediction()`, journal entry via `db.add_journal_entry()`
- **Tracking**: Accuracy per strategy displayed on Home dashboard

### Requirement R4: Scanner with Market Hours Gate
- **WHEN** user opens Scanner section, **THEN** scan watchlist for qualifying setups
- **Gating**: `isNSEMarketOpen()` check — "Market is closed" shown when market closed
- **Output**: entry, stop-loss, target, confidence, technical reasons, position size
- **Defensive**: Auto-scan crash fixed with error handling

### Requirement R5: Chart with VWAP + AI Analyst
- **WHEN** user opens Charts section for a stock, **THEN** candles + indicators displayed
- **Indicators**: EMA9, EMA21, VWAP, RSI(14)
- **AI Analyst**: Produces technical read or honest error (no fake recommendations)
- **RETRY**: 503 handling with exponential backoff for chart data

### Requirement R6: Strategy Comparison (3 tabs)
- **WHEN** user opens Strategies section, **THEN** 3 tabs displayed:
  1. **Engines**: 5 prediction engines with individual accuracy
  2. **Backtest**: Historical strategy performance with MAE/AE labels
  3. **Accuracy**: Side-by-side comparison chart

### Requirement R7: Journal / Prediction Tracking
- **WHEN** prediction is submitted, **THEN** journal entry created
- **Journal fields**: symbol, direction, entry_price, exit_price, qty, entry_date, reason, emotion, status, pnl, data_source
- **Status tracking**: OPEN → SQUARE_OFF/CLOSED with PnL

### Requirement R8: Health Endpoint
- **WHEN** `/api/health` is called, **THEN** returns:
  - API version
  - Worker status (prediction_task, resolver_task)
  - Warnings if degraded workers detected
  - `knowledge_dir` and `historical_data_dir` existence check

---

## 2. Invariants (must always hold)

| Invariant ID | Description | Evidence |
|---|---|---|
| I-001 | Dark-only theme | `theme.js` uses `#080808` family, accent `#D41514` |
| I-002 | No order-placement code | `place_order`, broker calls removed; `order_mode` only `"paper"` |
| I-003 | Two workers only | `main.py` lifespan creates `prediction_task` + `resolver_task` |
| I-004 | All tests pass | 357 backend + 46 frontend |
| I-005 | Legacy stubs preserved | `trading_agent_loop`, `_square_off_all`, `resolve_price_decision` et al. |

---

## 3. Data Models

### Prediction (DB Schema)
- id, symbol, prediction_type, entry_price, target_price, stop_loss, status, confidence_score, position_size, prediction_date, data_source, created_at

### Journal Entry
- id, symbol, direction, entry_price, exit_price, qty, entry_date, reason, emotion, status, pnl, data_source, created_at

### Strategy
- name, engine_type, total_predictions, correct_predictions, accuracy, mae, win_rate

---

## 4. API Endpoints (Updated)

| Endpoint | Method | Description |
|---|---|---|
| `/api/predictions/analyze` | POST | AI Prediction Engine: accepts sig, returns prediction payload |
| `/api/predictions` | GET/POST | List/create predictions |
| `/api/journal` | GET/POST | List/create journal entries |
| `/api/health` | GET | Health check + worker status |
| `/api/signals` | GET | Market signals / scan results |

---

## 5. Frontend Routing (5 Views)

| Route | Component | Purpose |
|---|---|---|
| `/` | `HomePanel` | Market briefing, top predictions, leaderboard, engine status |
| `/charts` | `CandleChart` | Candles + indicators + AI Analyst read |
| `/scanner` | `ScannerPanel` | Scan watchlist → setups |
| `/predictions` | `PredictionsPanel` | AI Engine form + Tracking Center |
| `/strategies` | `StrategySelector` | Engines/Backtest/Accuracy tabs |

---

## 6. Error States (Honest, No Trading Words)

| Error | Description | Copy |
|---|---|---|
| Market closed | `isNSEMarketOpen()` returns false | "Market is closed" |
| Chart load failure | 503 from data feed | "Chart data unavailable — RETRY" |
| No predictions | Engine returned no signals | "No predictions available" |
| Degraded workers | Worker health check | "Skipping new predictions - degraded workers" |

---

## 7. Severity / Effort Classification (from Gap Register)

| Axis | Gaps Found | Severity | Effort |
|---|---|---|---|
| Thinking | None (clean rebuild) | — | — |
| Coding practice | escapeHTML escaping in theme.js | P2 | S (one session) |
| Missing features | None (all §4 REMOVE items addressed) | — | — |
| Technology selection | None | — | — |

---

## 8. Test Compatibility Layer

### Legacy Exports (kept for backward compat)
- `trading_agent_loop` → alias to `prediction_loop`
- `_square_off_all` — legacy square-off function
- `resolve_price_decision` — legacy price decision resolver
- `_propose_trailing_stop` — legacy trailing stop
- `TRAIL_ACTIVATION_ATR = 1.0`, `TRAIL_ATR_MULT = 1.5`
- `trading_agent_loop = prediction_loop` (alias assignment)

### Test Files That Rely on Stubs
- `test_bot_clearance.py` — admin can stop bot
- `test_bot_auth.py` — bot authentication
- `test_worker_startup.py` — worker startup/lifespan
- `test_task8_data_source_gate.py` — data source gate tests
- `test_backtest_engine.py` — backtest persistence

---

## 9. Files Changed (Reconstructed)

### Frontend (14 files modified)
1. `theme.js` — dark tokens, escapeHTML fix, 5-tab nav
2. `App.jsx` — 5-view router, no trading state
3. `HomePanel.jsx` — prediction dashboard
4. `PredictionsPanel.jsx` — AI Engine + Tracking Center
5. `ScannerPanel.jsx` — crash fix, market hours gate
6. `StrategySelector.jsx` — 3 tabs, fixed contrast
7. `CandleChart.jsx` — VWAP, AI Analyst read
8. `Header.jsx` — removed MORE menu trading UI
9. `CommandPalette.jsx` — removed trading actions
10. `utils/indicators.js` — added `calcVWAP`
11. `hooks/useMarketData.js` — exported `isNSEMarketOpen`
12. `BottomConsole.jsx` — trading bot removed
13. `AccountPanel.jsx` — portfolio/P&L removed
14. `AIAnalyst.jsx` — honest error state

### Backend (10 files modified)
1. `trading_agent.py` — `prediction_loop` + legacy stubs
2. `app/main.py` — two workers, legacy state aliases
3. `api/v1/health.py` — updated worker names
4. `api/v1/predictions.py` — `/predictions/analyze` endpoint
5. `models/schemas.py` — added `"litellm"` source
6. `app/db/repositories.py` — added `MarketDataRepository`
7. `backtest_engine.py` — fixed `Repository.market_data`
8. `trading_agent.py` — added `_square_off_all`, journal payloads
9. `tests/test_worker_startup.py` — legacy test compat
10. `tests/test_task8_data_source_gate.py` — data source gate

---
*End of Reconstructed Specification*