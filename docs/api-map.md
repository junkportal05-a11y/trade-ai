# ApexTrade V3 - API Inventory

## API INVENTORY

| Method | Route | Purpose | Used By |
|---|---|---|---|
| `POST` | `/api/login` | Authenticate user & start session | `LoginScreen.jsx` |
| `POST` | `/api/logout` | Invalidate current session | `App.jsx` (Header) |
| `GET` | `/api/auth/verify` | Verify token & roles | `App.jsx` (on mount) |
| `GET` | `/api/quote` | Fetch live market quote | `useMarketData.js` |
| `GET` | `/api/history` | Retrieve prediction/trade history | `JournalPanel.jsx` |
| `GET` | `/api/search` | Search NSE symbol configs | `App.jsx` (Search Bar) |
| `GET` | `/api/market_brief` | Summarize current NSE market state | `HomePanel.jsx` |
| `POST` | `/api/scan` | Trigger NIFTY50 market scan | `ScannerPanel.jsx` |
| `GET` | `/api/signals` | Retrieve pending unexecuted signals | `SignalsPanel.jsx` |
| `GET` | `/api/signal/{symbol}` | Get specific signal details | `SignalsPanel.jsx` |
| `POST` | `/api/allocate` | Get capital allocation | `ScannerPanel.jsx` |
| `POST` | `/api/angelone/login` | Connect backend to AngelOne | `BrokerSettings.jsx` |
| `GET` | `/api/angelone/status` | Check broker connection status | `BrokerSettings.jsx` |
| `POST` | `/api/predictions` | Submit a paper/live trade | `SignalsPanel.jsx` / `App.jsx` |
| `GET` | `/api/predictions` | Retrieve active trades | `PredictionsPanel.jsx` |
| `GET` | `/api/predictions/stats` | Aggregated performance stats | `PredictionsPanel.jsx` / `HomePanel.jsx` |
| `POST` | `/api/predictions/{id}/resolve`| Manually resolve active trade | `PredictionsPanel.jsx` |
| `DELETE` | `/api/predictions/{id}` | Remove prediction | `PredictionsPanel.jsx` |
| `GET` | `/api/journal` | Retrieve trading journal entries | `JournalPanel.jsx` |
| `POST` | `/api/journal` | Create new journal entry | `JournalPanel.jsx` |
| `DELETE` | `/api/journal/{id}` | Delete entry | `JournalPanel.jsx` |
| `POST` | `/api/chat` | AI chat interface | `App.jsx` (ChatPanel) |
| `GET` | `/api/backtest/run` | Execute historical backtest | `SimulatorPanel.jsx` |
| `GET` | `/api/backtest/stats` | Aggregated performance stats | `SimulatorPanel.jsx` |
| `GET` | `/api/backtest/history` | Raw backtest signal logs | `SimulatorPanel.jsx` |
| `POST` | `/api/backtest/reset` | Clear backtest database | `SimulatorPanel.jsx` |
