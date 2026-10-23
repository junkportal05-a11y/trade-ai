# ApexTrade V3 - Project Memory

## Project Overview
ApexTrade V3 is an autonomous, quantitative trading system designed specifically for the Indian Stock Market (NSE). It provides an end-to-end pipeline for market data ingestion, technical analysis, signal generation, trade quality scoring, and automated execution via the AngelOne SmartAPI.

## Business Purpose
The primary goal is to remove human emotion from intraday trading by enforcing strict mathematical boundaries, rigorous risk management (capital allocation and drawdown limits), and technical criteria. It targets high win rates and mathematically sound risk-to-reward ratios.
- **Users**: Quantitative Traders, Risk Managers.
- **Primary Entities**: Signals, Predictions (Trades), Journal Entries, Portfolio Snapshots.
- **User Workflow**: User logs in -> Dashboard views market brief -> Scans for setups -> Agent executes setups (or user manually triggers) -> Predictions are resolved automatically -> Performance is analyzed.

## Tech Stack
- **Frontend**: React, Vite, Lightweight-Charts
- **Backend**: Python 3.11, FastAPI
- **Database**: SQLite (`trade_ai.db`)
- **Authentication**: Custom token-based (bcrypt)
- **Infrastructure**: Vercel (Frontend), Docker / Hugging Face Spaces (Backend)

## Repository Structure
- `backend/`: FastAPI application, Python core logic, strategies, API endpoints, `Dockerfile`.
- `frontend/`: React SPA, Vite configuration, UI components, `package.json`, `vercel.json`.
- `knowledge/`: Reference documentation and agent guidelines.
- `historical_data/`: Downloaded Parquet files for backtesting.
- `scratch/`: Agent scratchpads and analysis scripts.

## System Architecture
A split monolithic architecture. 
Browser ↓ Frontend (React SPA) ↓ API Layer (FastAPI) ↓ Business Logic (signals/agent) ↓ Database (SQLite)

## Routing Map
- **Backend**: FastAPI Router (`main.py`, `backtest_routes.py`). All routes are prefixed with `/api/`.
- **Frontend**: State-based conditional rendering in `App.jsx` based on `activeTab` (e.g., `dashboard`, `scanner`, `signals`).

## Frontend Architecture
- **Component Hierarchy**: `LoginScreen` or `App` -> `Header`, `HomePanel`, `SignalsPanel`, `PredictionsPanel`, `ScannerPanel`.
- **State Management**: React Context / Hooks (`useState`, `useEffect`). Global data managed via `useMarketData.js`.
- **Data Source**: Custom `apiFetch` wrapper connecting to the backend via HTTP REST.

## Backend Architecture
- **Controllers**: API Endpoints in `main.py`.
- **Services**: `signals.py` (Analysis), `trading_agent.py` (Execution), `trade_quality.py` (Scoring).
- **Middleware**: Custom session token validation (`auth_helpers.require_session`).
- **Workers**: `governance_worker.py` (Risk), `prediction_resolver_worker` (Trade tracking).

## Database Architecture
SQLite-based persistence (`trade_ai.db`).
- `signals_history`: Candidate trades.
- `predictions`: Executed trades.
- `journal_entries`: Manual trading notes.
- `data_quality`: Integrity scores.
- `portfolio_snapshots`: Daily equity.

## Authentication Flow
**AUTH FLOW:**
1. User submits password to `POST /api/login`.
2. Backend validates against bcrypt hashes stored in memory (loaded from `.env`).
3. Backend generates `apt_...` token and stores in `ACTIVE_SESSIONS` dict.
4. Frontend stores token in `sessionStorage` / `localStorage`.
5. Every subsequent request passes token in `x-session-token` header or `Authorization: Bearer`.
6. Middleware (`require_session`) validates token.
7. `POST /api/logout` deletes token from memory.

## API Inventory
Refer to `api-map.md` for full breakdown. Primary endpoints interact with `/api/predictions` for trades and `/api/signals` for setups.

## Data Flow Diagrams
**Major Feature: Scan and Auto-Execute**
User Action (or Cron) ↓ Frontend triggers `/api/scan` ↓ API calls `signals.py` ↓ Business Logic scores via `trade_quality.py` ↓ Database saves to `signals_history` ↓ Background `trading_agent.py` picks it up and executes ↓ Database saves to `predictions` ↓ Response 200 OK ↓ UI Updates automatically on next poll.

## Environment Variables
- `ADMIN_KEY`, `SECRET_KEY`: Backend security mechanisms.
- `PASS_ADMIN`, `PASS_USER1`: Passwords.
- `ANGEL_API_KEY`, `ANGEL_CLIENT_ID`, `ANGEL_PIN`, `ANGEL_TOTP_SECRET`: Broker connection.
- `GEMINI_API_KEY`, `NEWS_API_KEY`: Third-party intelligence.

## Third Party Integrations
- **AngelOne SmartAPI**: Live data and order execution.
- **NewsAPI** & **Google Gemini**: Sentiment analysis.
- **Yahoo Finance**: Historical data mining.

## Feature Inventory
| Name | Purpose | Frontend Files | Backend Files | Database Tables | External Services | Dependencies |
|---|---|---|---|---|---|---|
| **Autonomous Agent** | Auto-execute trades | `PredictionsPanel.jsx` | `trading_agent.py`, `prediction_resolver_worker` | `predictions` | AngelOne | `asyncio` |
| **Scanner** | Identify technical setups | `ScannerPanel.jsx` | `signals.py`, `candlestick_patterns.py` | `signals_history` | yfinance | `pandas` |
| **Governance Engine** | Daily loss kill switches | `HomePanel.jsx` | `governance_worker.py` | `portfolio_snapshots` | None | None |
| **Data Validator** | Lock UI on bad data | `HomePanel.jsx` | `data_validator.py` | `data_quality` | None | None |
| **News Sentiment** | LLM news scoring | N/A | `news_feed.py` | None | NewsAPI, Gemini | `google-genai` |

## Dependency Graph
Refer to `dependency-graph.md`.
Critical path: `main.py` -> `trading_agent.py` -> `signals.py` -> `db.py`.

## Important Files
- `backend/signals.py`: Core logic.
- `backend/trade_quality.py`: Risk filter.
- `backend/main.py`: API Gateway.
- `frontend/src/api.js`: Client fetcher.

## Performance Notes
- `signals.py` uses Pandas vectorized operations.
- `numba.py` is mocked. True compilation would improve indicator speed.
- `data_validator.py` checks flatlines, which is computationally expensive on large dataframes.

## Technical Debt
- In-memory `ACTIVE_SESSIONS` causes session loss on server restart.
- State-based routing in React prevents direct deep-linking to pages.
- No formal message queue (e.g., Redis); relies on `asyncio.sleep` loops.

## Development Workflow
Local execution: `uvicorn main:app` for backend, `npm run dev` for frontend.

## Deployment Process
Backend: `Dockerfile` exposing port 7860 (Hugging Face Spaces compatible).
Frontend: Vercel deployment via `vercel.json` rewrites.

## Known Risks
- AngelOne WebSocket disconnects can cause missed stop-loss triggers.
- Ephemeral backend memory state.

## Future Recommendations
- Migrate to Postgres/Redis for stateless backend scaling.
- Implement `react-router-dom` in the frontend.
- Implement WebSockets for UI updates instead of HTTP polling.

## Agent Directives
- **Deep Check Validation:** Never blindly check off pre-requisites or tasks merely because a file exists. Always perform a deep check: verify that environment variables exist, imports are correct, functions are actively called, and execution paths are fully integrated.

## Recent Updates
- Added bot state handling (RUNNING, PAUSED, STOPPED) in `db.py` (`get_bot_state`/`set_bot_state`), `trading_agent.py` (loop gate), `bot.py` (new router), and `router.py` (included `bot.router`).
- Modified `BotControlPanel.jsx` and `TradeLogPanel.jsx` to call real `/api/bot/*` endpoints and parse the new response shapes (`state`, `today_pnl`, `last_signal`, `positions`, `trades`).
- New endpoints: `POST /api/bot/start`, `POST /api/bot/pause`, `POST /api/bot/stop` (triggers `_square_off_all`), `GET /api/bot/status`, `GET /api/bot/trades`.
- Ran `graphify update .` to refresh the dependency graph after code changes (3033 nodes, 3948 edges).
- Cleaned up debug regex files and confirmed Vite build success.
