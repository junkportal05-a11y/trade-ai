# PHASE 1C — Backend Bot Integration (API & Control)

> Goal: Connect the new React Bot Engine UI to the Python backend so the user can control the trading agent, view its status, and see its live trades.

## Task 2.1 — Bot State Management
- [x] Add a `bot_state` key to the `app_settings` database table to track if the bot is `RUNNING`, `PAUSED`, or `STOPPED`.
- [x] Update `trading_agent.py` to check this state at the top of its `while True` loop:
  - If `STOPPED`, skip scan or break.
  - If `PAUSED`, skip the scan but maintain open positions (monitor SL/TP).
  - If `RUNNING`, execute full logic.

## Task 2.2 — Bot Control API Endpoints
- [x] **File:** `backend/app/main.py` (or a new router `bot.py`)
- [x] `POST /api/bot/start` -> Sets state to `RUNNING`.
- [x] `POST /api/bot/pause` -> Sets state to `PAUSED`.
- [x] `POST /api/bot/stop` -> Sets state to `STOPPED` and triggers `_square_off_all()`.
- [x] `GET /api/bot/status` -> Returns the current state, today's P&L, last signal, and current positions.
- [x] `GET /api/bot/trades` -> Returns the live trade log (recent predictions with status PENDING/WIN/LOSS/TIMEOUT).

## Task 2.3 — Frontend Wiring
- [x] Ensure `BotControlPanel.jsx` makes calls to these endpoints instead of mock data.
- [x] Ensure `TradeLogPanel.jsx` polls `/api/bot/trades` every 3 seconds.
- [x] Ensure `SimulatorPanel.jsx` / `BotControlPanel` fetches `/api/bot/status` periodically.
