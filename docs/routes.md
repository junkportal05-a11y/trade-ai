# ApexTrade V3 - Routes Map

## ROUTES TABLE (Backend)

| Route | File | Purpose | Auth Required |
|---|---|---|---|
| `POST /api/login` | `backend/main.py` | Authenticate user | No |
| `POST /api/logout` | `backend/main.py` | Invalidate session | Yes |
| `GET /api/auth/verify` | `backend/main.py` | Verify session token | Yes |
| `GET /api/quote` | `backend/main.py` | Fetch live market quote | Yes |
| `GET /api/history` | `backend/main.py` | Retrieve past trades | Yes |
| `GET /api/search` | `backend/main.py` | Symbol lookup | Yes |
| `GET /api/market_brief` | `backend/main.py` | Get overall market state | Yes |
| `POST /api/scan` | `backend/main.py` | Trigger NIFTY50 scan | Yes |
| `GET /api/signals` | `backend/main.py` | Get pending signals | Yes |
| `GET /api/signal/{symbol}` | `backend/main.py` | Get specific signal | Yes |
| `POST /api/allocate` | `backend/main.py` | Capital allocation | Yes |
| `POST /api/angelone/login` | `backend/main.py` | Connect to broker | Yes |
| `GET /api/angelone/status` | `backend/main.py` | Broker status check | Yes |
| `POST /api/predictions` | `backend/main.py` | Place a trade | Yes |
| `GET /api/predictions` | `backend/main.py` | List active trades | Yes |
| `GET /api/predictions/stats`| `backend/main.py` | Aggregated performance | Yes |
| `POST /api/predictions/{id}/resolve`| `backend/main.py`| Manual resolution | Yes |
| `DELETE /api/predictions/{id}`| `backend/main.py`| Delete trade record | Yes |
| `GET /api/journal` | `backend/main.py` | List journal entries | Yes |
| `POST /api/journal` | `backend/main.py` | Add journal entry | Yes |
| `DELETE /api/journal/{id}` | `backend/main.py` | Delete journal entry | Yes |
| `POST /api/chat` | `backend/main.py` | AI chat query | Yes |
| `GET /api/backtest/run` | `backend/backtest_routes.py`| Run historical backtest | Yes |
| `GET /api/backtest/stats` | `backend/backtest_routes.py`| Backtest aggregate stats| Yes |
| `GET /api/backtest/history`| `backend/backtest_routes.py`| Backtest signal history | Yes |
| `POST /api/backtest/reset` | `backend/backtest_routes.py`| Clear backtest DB | Yes (Admin) |

## ROUTES TABLE (Frontend)
*Note: The frontend does not use standard URL routing (like React Router). It uses conditional state rendering based on the `activeTab` variable.*

| Route (State) | File | Purpose | Auth Required |
|---|---|---|---|
| `login` | `frontend/src/LoginScreen.jsx` | User login entry point | No |
| `dashboard` | `frontend/src/HomePanel.jsx` | Main overview dashboard | Yes |
| `scanner` | `frontend/src/ScannerPanel.jsx` | Scan execution & view | Yes |
| `signals` | `frontend/src/SignalsPanel.jsx` | Pending signals view | Yes |
| `predictions` | `frontend/src/PredictionsPanel.jsx`| Active trades management | Yes |
| `journal` | `frontend/src/JournalPanel.jsx` | Trading journal log | Yes |
| `backtest` | `frontend/src/SimulatorPanel.jsx` | Simulation & Backtesting | Yes |
| `settings` | `frontend/src/AccountPanel.jsx` | Account & Broker settings | Yes |
