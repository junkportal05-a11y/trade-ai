# ApexTrade Architecture Blueprint: Floor-by-Floor Map

This map organizes the entire codebase like a multi-story building. When auditing, debugging, or troubleshooting, inspect **Floor by Floor** from the ground up.

---

```
                       [ ROOFTOP (Floor 7) ]
                DevOps, Containers, CI/CD & Deployments
                                │
                       [ FLOOR 6: FRONTEND UI ]
               React, Tailwind/CSS, Components & Panels
                                │
                  [ FLOOR 5: REAL-TIME & WEBSOCKETS ]
              WS Streams, Price Feeds, Live Broadcasts
                                │
                    [ FLOOR 4: API & ROUTING ]
           FastAPI Routers, Endpoints, Auth & CSRF Guards
                                │
                   [ FLOOR 3: TRADING & QUANT ENGINE ]
          Tournament, Signal Generators, Bot & Sizing
                                │
                    [ FLOOR 2: AI & LLM SERVICES ]
         Local Ollama, LiteLLM, Proxy & Decision Engines
                                │
                 [ FLOOR 1: DATA & PERSISTENCE ]
           PostgreSQL / SQLite, SQLAlchemy Models, Validations
                                │
                   [ FLOOR 0: THE FOUNDATION ]
          Core Config, Secrets, Security Primitives, Rate Limits
```

---

## 🏢 Floor 0: The Foundation (Core Config & Security Primitives)
*The bedrock of the entire application. If there is an issue here, everything above breaks.*

| Component | Primary Files | Key Responsibilities & Watchouts |
| :--- | :--- | :--- |
| **App Configuration** | `backend/app/core/config.py` | Environment variables, database URLs, token timeouts, secret parsing. |
| **Security & Auth Core**| `backend/app/core/security.py` | JWT creation/verification, password hashing, admin auth, CSRF headers. |
| **Rate Limiter** | `backend/app/core/limiter.py` | Real client IP extraction, request throttling, anti-abuse. |
| **Logging & Telemetry**| `backend/app/core/logging.py` | Unified structured logging. |

---

## 🏢 Floor 1: Data & Persistence (Database & Models)
*Storage, migrations, data integrity checks, and historical schemas.*

| Component | Primary Files | Key Responsibilities & Watchouts |
| :--- | :--- | :--- |
| **DB Session & Engine**| `backend/app/db/session.py` | Connection pooling, transaction lifecycle, SQLite/Postgres compatibility. |
| **ORM Models** | `backend/app/db/models.py` | User, Prediction, Trade, Strategy, Journal tables. |
| **Migrations** | `backend/app/db/migrations.py` | Schema evolution, auto-table creation, index definitions. |
| **Data Validation** | `backend/data_validator.py` | OHLCV sanity, anomaly detection, feed confidence score. |

---

## 🏢 Floor 2: AI & LLM Engine (Local Intelligence & Proxy)
*The cognitive center: reasoning agents, chat services, and prompt orchestrators.*

| Component | Primary Files | Key Responsibilities & Watchouts |
| :--- | :--- | :--- |
| **Proxy Server** | `C:\Users\aryan\openrouter-proxy-server\server.js` | Key rotation, model fallback, streaming parser on port 3000. |
| **AI Strategy Bot** | `backend/ai_engine.py`, `backend/ai_validator.py` | Signal vetting, risk validation via LLM prompt rules. |
| **Chat & Assistance** | `backend/app/services/chat.py` | Trade assistant chat completions, context pruning. |

---

## 🏢 Floor 3: Trading & Quant Engine (Algorithms & Execution)
*Strategy tournament, signal generation, position sizing, and broker execution.*

| Component | Primary Files | Key Responsibilities & Watchouts |
| :--- | :--- | :--- |
| **Tournament Engine**| `backend/strategy_tournament.py` | 30 quant strategies benchmarked across timeframes. |
| **Signal Generators** | `backend/signals.py` | Technical indicators (EMA, RSI, MACD, Supertrend, Breakout). |
| **Trading Agent** | `backend/trading_agent.py` | Automated order lifecycle, stop-loss / target tracking, square-offs. |
| **Position Sizing** | `backend/app/services/allocate.py` | Kelly criterion, volatility-adjusted position allocation. |
| **Bot Trainer** | `backend/bot_trainer.py` | Walk-forward optimization and parameter evolution. |

---

## 🏢 Floor 4: API & Routing (FastAPI Web Layer)
*HTTP interface, request authorization, input validation, and business endpoints.*

| Component | Primary Files | Key Responsibilities & Watchouts |
| :--- | :--- | :--- |
| **Router Aggregator** | `backend/app/api/v1/router.py` | Global router registration, CSRF dependency attachments. |
| **Auth & Users** | `backend/app/api/v1/auth.py` | Login, register, JWT cookie issuance, token refresh. |
| **Signals & Quotes** | `backend/app/api/v1/signals.py`, `quotes.py` | Market feed delivery, technical scan triggers. |
| **Broker Operations** | `backend/app/api/v1/broker.py` | Portfolio holding sync, manual & automated orders. |
| **Journal & Analytics**| `backend/app/api/v1/journal.py`, `predictions.py` | Trade logging, EV calculation, post-trade audit. |
| **Admin & Control** | `backend/app/api/v1/admin.py`, `bot.py` | System health, tournament controls, kill switches. |
| **Webhooks (n8n)** | `backend/app/api/v1/n8n.py` | External workflow automation with timing-safe webhook secret. |

---

## 🏢 Floor 5: Real-Time & WebSockets (Live Data Streams)
*Bi-directional low-latency communications.*

| Component | Primary Files | Key Responsibilities & Watchouts |
| :--- | :--- | :--- |
| **WebSocket Handler** | `backend/app/api/v1/ws.py` | Auth precedence (Cookie -> Query token), connection manager. |
| **Market Data Feeds** | `backend/app/services/market_data.py` | Live tick dispatch, orderbook broadcast, heartbeat ping/pong. |

---

## 🏢 Floor 6: Frontend UI (Client Application)
*User interface, interactive charts, real-time controls, and state management.*

| Component | Primary Files | Key Responsibilities & Watchouts |
| :--- | :--- | :--- |
| **Root & Router** | `frontend/src/App.jsx`, `main.jsx` | App shell, navigation, global auth state, toast notifications. |
| **Trading Panels** | `frontend/src/SignalsPanel.jsx`, `ScannerPanel.jsx` | Live signal boards, strategy filtering, one-click execution. |
| **Quant Tournament** | `frontend/src/TournamentPanel.jsx` | Leaderboards, win-rate heatmaps, equity curve visualizers. |
| **Predictions & AI** | `frontend/src/PredictionsPanel.jsx`, `ChatPanel.jsx` | Model accuracy stats, AI chat dialogue interface. |
| **Hooks & State** | `frontend/src/hooks/useMarketData.js`, `useAuth.js` | Auto-reconnecting WebSockets, CSRF-aware fetch wrappers. |

---

## 🏢 Floor 7: Rooftop (DevOps, Tests & Quality Gates)
*Testing framework, build scripts, packaging, and deployment.*

| Component | Primary Files | Key Responsibilities & Watchouts |
| :--- | :--- | :--- |
| **Test Suites** | `backend/tests/` (150+ tests) | Security regression tests, engine mocks, endpoint tests. |
| **Build & Pack** | `repomix.config.json`, `package.json` | `codebase.md` packing, Vite bundler config. |
| **Docker & Deploy** | `docker-compose.yml`, `Dockerfile` | Container orchestration, environment isolation. |
