# ApexTrade Rebuild - Implementation Plan

## Overview
Transform ApexTrade from a trading bot into a pure prediction/analysis platform with 5 navigation sections.

---

## Phase 0: Deployment Pinning (MUST DO FIRST)

### 0.1 Verify Vercel Build Source
- Check Vercel project settings → Git → Connected repository & branch
- Confirm it builds from `main` branch

### 0.2 Verify Hugging Face Space Entry Point
- Check HF Space settings → Repository → Branch
- Check which entry point is used: `backend/Procfile` (`uvicorn main:app`) or `backend/Dockerfile` (`uvicorn app.main:app`)
- Reconcile to single entry point

### 0.3 Verify Live Parity
- Fetch live JS bundle 3x, confirm identical layouts/win rates

---

## Phase 1: Navigation Restructure

### 1.1 Update `theme.js` - New Tab Configuration
```javascript
// OLD: 8 primary + 3 secondary + MORE menu
// NEW: 5 primary only
export const PRIMARY_TABS = ['HOME', 'CHART', 'SIGNALS', 'PREDICTIONS', 'STRATEGIES'];
export const SECONDARY_TABS = [];  // DELETED
export const MOBILE_TABS = ['HOME', 'CHART', 'SIGNALS', 'PREDICTIONS', 'STRATEGIES'];

export const TAB_META = {
  HOME: { label: 'Home', icon: 'Home' },
  CHART: { label: 'Charts', icon: 'TrendingUp' },
  SIGNALS: { label: 'Scanner', icon: 'Radio' },
  PREDICTIONS: { label: 'Predictions', icon: 'Sparkles' },
  STRATEGIES: { label: 'Strategies', icon: 'Settings' },
};
```

### 1.2 Update `Header.jsx` - Remove MORE Menu & Portfolio/P&L
- Remove `SECONDARY_TABS` MORE dropdown
- Remove Portfolio/P&L/Cash/Holdings display (lines 277-298)
- Remove System Health button (lines 384-417) - replace with small engine status on Home
- Keep: Ticker, Symbol/Price, Command Palette, Latency, Clock, Version

### 1.3 Update `App.jsx` - View Routing
- Remove: `SIMULATOR` (Bot Engine), `JOURNAL`, `PERFORMANCE`, `ACCOUNT`
- Keep: `HOME`, `CHART`, `SIGNALS`, `PREDICTIONS`, `STRATEGIES`
- Update `MobileNavButtons` to use new 5 tabs

---

## Phase 2: Remove Deleted Features (Code & Database)

### 2.1 Frontend Components to DELETE
| Component | File | Notes |
|-----------|------|-------|
| BotControlPanel | `frontend/src/BotControlPanel.jsx` | Entire trading bot UI |
| TradeLogPanel | `frontend/src/TradeLogPanel.jsx` | Trading log |
| AccountPanel | `frontend/src/AccountPanel.jsx` | Security page |
| BrokerSettings | `frontend/src/BrokerSettings.jsx` | AngelOne connection |
| ChatPanel | `frontend/src/components/ChatPanel.jsx` | Chat UI |
| SystemHealthModal | `frontend/src/components/SystemHealthModal.jsx` | Diagnostics panel |
| OrderPanel | `frontend/src/components/OrderPanel.jsx` | Order entry |
| OrderBookPanel | `frontend/src/OrderBookPanel.jsx` | Order book |
| PortfolioPanel | `frontend/src/components/PortfolioPanel.jsx` | Portfolio view |
| PerformancePanel | `frontend/src/PerformancePanel.jsx` | Analytics (moves to Strategies) |
| JournalPanel | `frontend/src/JournalPanel.jsx` | Journal (folds into Predictions) |
| SimulatorPanel | `frontend/src/SimulatorPanel.jsx` | Bot Engine view |

### 2.2 Remove from `App.jsx` Imports & Usage
- Remove all imports of deleted components
- Remove state: `portfolio`, `cash`, `openOrders`, `tradeMarkers`, `botPaperMode`, `selectedStrategy`, `strategyPerformance`, `backtestResults`, `consoleTab`, `priceAlerts`, `signals`, `marketBrief`, `loadingBrief`, `briefError`, `predictionStats`, `refreshAnalystToken`, `aiRecommendation`, `aiRecommendationSource`, `aiRecommendationError`, `aiRecommendationLoading`, `aiRecommendationCache`, `lastRefreshRef`, `toasts`, `pendingPredictions`, `resolvingIds`, `fetchPendingPredictions`, `handleCommandAction` (emergency-stop, clear-logs), `handleToggleFavorite`, `handleAddAlert`, `handleDeleteAlert`, `handleExecuteOrder`, `handleCancelOrder`, limit order matching effect, `handleSignalSelect`, `handleWokenUp`

### 2.3 Backend - Remove Order/Trading Code
| File | What to Remove |
|------|----------------|
| `backend/app/api/v1/bot.py` | Entire file - DELETE |
| `backend/app/api/v1/broker.py` | Entire file - DELETE (AngelOne for orders) |
| `backend/trading_agent.py` | KEEP only `prediction_resolver_worker`; DELETE `trading_agent_loop` |
| `backend/governance_worker.py` | DELETE - governance loop |
| `backend/app/services/signal_engine.py` | KEEP for signal generation |
| `backend/signals.py` | KEEP for analysis |
| `backend/app/main.py` | Remove `governance_task` startup; keep only `agent_task` (renamed to prediction_loop) and `resolver_task` |

### 2.4 Database - Remove Tables (if unused)
- `signals_history` - used by Scanner? Keep for now
- `trade_journal` - KEEP (used by Predictions for manual logs)
- `predictions_history` - KEEP (core)
- `rejected_signals` - Keep for Scanner gate breakdown
- `equity_curve` - DELETE (trading P&L)
- `portfolio_state` - DELETE
- `risk_settings` - DELETE
- `daily_governance_reports` - DELETE

---

## Phase 3: Fix & Rebuild Kept Features

### 3.1 Charts (was Terminal) - `CandleChart.jsx` + Chart Page
**Bugs to Fix:**
- Candles must load for RELIANCE 1m without RETRY (check `/api/history` 503 handling)
- Indicators: EMA9, EMA21, VWAP, RSI(14) - already implemented
- Right panel tabs: Chart, Strategies, Backtest, AI Analyst (remove POSITIONS, TRADE LOG, BOT ENGINE)
- AI Analyst Refresh: must produce read or honest error (not spin 20s then show "no priced context")

**Changes:**
- Update right panel tabs in Chart view
- Fix AI Analyst panel to use `/api/chat/chart` properly
- Ensure synthetic data shows "SIMULATED" label

### 3.2 Scanner - `ScannerPanel.jsx`
**Bugs to Fix:**
- **CRASH FIX**: Auto-scan crashes app - wrap `POST /api/allocate` in try/catch, handle empty/failed/slow response
- **FALSE LABEL FIX**: "Market is closed" shows when market is open but zero signals → use `isNSEMarketOpen` from `useMarketData.js:305`
  - Market genuinely closed → keep label
  - Market open + zero signals → "No qualifying setups — the scan ran but no signal passed the gates" + per-gate rejection breakdown
- SCAN & SIZE action must be reachable

### 3.3 Predictions (was Predictions + Journal) - `PredictionsPanel.jsx`
**Changes:**
- Restore AI Prediction Engine form (symbol, timeframe, ANALYZE & PREDICT) - was replaced by Tracking Center
- Keep Prediction Tracking Center: RECORD NEW SYSTEM PREDICTION form + prediction log
- Fix modal layout: Exit Price / Total PnL fields stuck out past modal edge
- **PREDICTION RESOLVER MUST RUN**: Background worker resolves predictions → updates accuracy per strategy

### 3.4 Strategies (was Strategies tab + Analytics + Backtest) - `StrategySelector.jsx` + new Backtest
**Bugs to Fix:**
- Trend Scalper card contrast (white bg, washed-out text)
- Backtest RUN must complete: fix "'Repository' object has no attribute 'market_data'"
- Leaderboard rows clickable → open strategy backtest details
- Analytics content moves here: accuracy per strategy, resolved counts, 5-strategy comparison

### 3.5 Home (Prediction Dashboard) - `HomePanel.jsx`
**Keep:**
- AI Daily Market Briefing (NIFTY bias, top picks)
- Top Screening Trigger
- Predictions Accuracy
- Strategy leaderboard
- Engine status line (prediction loop running/stopped, last scan time, feed status)

**Remove:**
- Portfolio Balances, Holdings Allocation donut
- AI Quant Mentor recommendation
- Active Price Alerts

**Links must navigate:**
- PREDICTIONS CENTRE → Predictions page
- OPEN SIGNAL SCANNER → Scanner page
- OPEN INTERACTIVE CHARTS → Charts page

---

## Phase 4: Backend - Two Background Jobs

### 4.1 Prediction Loop (replaces `trading_agent_loop`)
- Runs strategies on schedule during market hours
- Records predictions to `predictions_history`
- **NO ORDER PLACEMENT** - pure prediction recording

### 4.2 Prediction Resolver (keep `prediction_resolver_worker`)
- Polls pending predictions
- Records outcome (right/wrong) when target/stop hit
- Updates accuracy per strategy

### 4.3 Remove Governance Worker
- Delete `governance_worker.py`
- Remove from `main.py` startup

### 4.4 Backend Fixes
- Fix `ChatResponse` schema: add `"litellm"` to allowed sources
- Restore `knowledge_dir` and `historical_data_dir` or confirm intentionally absent
- Remove stale localhost URLs from frontend bundle

---

## Phase 5: UI/UX Rules Implementation

### 5.1 Theme Updates (`theme.js`)
- Dark only: `#080808` family, accent `#D41514`, light text `#CDCBCA`
- No glassmorphism, gradients, colored cards
- Auth gate stays flat `#0b0e13` / `#12161d`

### 5.2 Command Palette - `CommandPalette.jsx`
- Keep: Navigation + Symbol search
- Remove: Emergency Stop Bot, Clear Order Logs
- Fix "undefined ·" label bug on symbols

### 5.3 Honest Empty States
- No blank black areas
- No spinners that never resolve
- No invented numbers
- Empty = sentence explaining what's empty and why

---

## Phase 6: Final Verification (Live Site)

### 6.1 Checklist (All on LIVE site after deploy)
- [ ] Three separate loads show identical layouts & strategy win rates
- [ ] Navigation: exactly 5 sections (Home, Charts, Scanner, Predictions, Strategies)
- [ ] No Bot Engine, Journal, Security, Analytics, MORE menu
- [ ] No trading words (BUY/SELL buttons, P&L, positions, stop loss, deploy)
- [ ] Charts: RELIANCE 1m loads without RETRY; indicators show; AI Analyst works
- [ ] Scanner: opens 3x without crash; market-open never says "Market is closed"; empty scan explains why
- [ ] Predictions: AI Engine form present; ANALYZE & PREDICT works; Tracking form records
- [ ] Prediction resolution works: recorded prediction gets outcome, accuracy updates from 0 of 0
- [ ] Strategies: 5 cards legible; backtest runs; leaderboard rows open details; accuracy comparison renders
- [ ] Home: briefing, trigger, accuracy, leaderboard, engine status render; 3 links navigate
- [ ] Command palette: nav + symbols work; no trading actions; no "undefined ·"
- [ ] No order-placement code in repo (grep `place_order` = nothing)
- [ ] No localhost URLs in built bundle
- [ ] `/api/health` no storage warning; AI status matches reality
- [ ] No bot trading state; prediction loop state on Home

---

## Phase 7: Documentation & Deploy

### 7.1 Update `codebase.md` to match final code
### 7.2 Commit, push, deploy to live
### 7.3 Verify live site once more after deploy

---

## Execution Order

1. **Phase 0** - Deployment pinning (BLOCKER - do first)
2. **Phase 1** - Navigation restructure (theme.js, Header.jsx, App.jsx)
3. **Phase 2** - Remove deleted features (massive cleanup)
4. **Phase 3** - Fix & rebuild kept features (Charts, Scanner, Predictions, Strategies, Home)
5. **Phase 4** - Backend two workers
6. **Phase 5** - UI/UX rules
7. **Phase 6** - Final verification
8. **Phase 7** - Deploy & verify

---

## Key Files to Modify

### Frontend
- `frontend/src/theme.js` - Tab config, colors
- `frontend/src/components/Header.jsx` - Remove MORE, portfolio, health button
- `frontend/src/App.jsx` - Main router, state cleanup
- `frontend/src/HomePanel.jsx` - Prediction dashboard
- `frontend/src/ScannerPanel.jsx` - Fix crash + false label
- `frontend/src/PredictionsPanel.jsx` - Restore AI Engine + fix resolver
- `frontend/src/StrategySelector.jsx` - Fix contrast, backtest, leaderboard
- `frontend/src/components/CandleChart.jsx` - Fix chart loading, AI Analyst
- `frontend/src/components/CommandPalette.jsx` - Remove trading actions
- `frontend/src/hooks/useMarketData.js` - Export `isNSEMarketOpen`

### Backend
- `backend/app/main.py` - Two workers only
- `backend/trading_agent.py` - Keep only resolver
- `backend/app/api/v1/predictions.py` - Stats/accuracy per strategy
- `backend/app/api/v1/health.py` - Storage dirs check
- `backend/app/services/chat.py` - Fix litellm source
- `backend/signals.py` - Ensure synthetic labeled
- `backend/app/api/v1/backtest.py` - Fix Repository.market_data

### Database (Alembic migration)
- Drop trading-related tables

---

## Notes

- **Single user**: `apex_head_quant`, `LEVEL_4_ROOT` - keep existing auth
- **No secrets in code** - env vars only
- **Test every change live** - feature done only when live site shows it
- **Work in order** - don't skip to UI polish while deployment unpinned