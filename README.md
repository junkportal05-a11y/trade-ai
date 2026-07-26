---
title: ApexTrade Quant Server
emoji: 📈
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# ApexTrade Quant Server

[![Build Status](https://github.com/apex-trade/trade-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/apex-trade/trade-ai/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19.2.6-61DAFB.svg?logo=react)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-8.0-646CFF.svg?logo=vite)](https://vitejs.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

ApexTrade is an advanced quantitative trading platform designed for real-time market analysis, automated technical signal generation, portfolio capital allocation, and performance tracking.

This repository hosts the code for both the **FastAPI backend** (deployed as a Docker space on Hugging Face) and the **React + Vite frontend** (deployed on Vercel).

---

## Architecture Overview

ApexTrade uses a decoupled architecture separating data visualization and user interaction from heavy quantitative computation and broker background execution daemons.

```mermaid
graph TD
    subgraph Client ["Client Layer (React + Vite SPA)"]
        UI["ApexCharts Terminal & UI"]
        Journal["Trade Journal Panel"]
        ScannerUI["Scanner & Signals Panel"]
        SimUI["Backtest & Simulator"]
    end

    subgraph Backend ["FastAPI Quantitative Engine"]
        API["FastAPI REST & WebSockets (/api/v1)"]
        
        subgraph Signals ["Quant Signal Engine"]
            Indicators["Vectorized Indicators (RSI, MACD, VWAP, OBV)"]
            Patterns["Candlestick Pattern Analyzer"]
            QualityEngine["Trade Quality Engine (0-100 Score)"]
        end

        subgraph Execution ["Execution & Risk Daemons"]
            AgentDaemon["Autonomous Trading Agent"]
            CapitalAlloc["Algorithmic Capital Allocator"]
            Governance["Governance Worker (Drawdown Kill-Switch)"]
            Resolver["Prediction Resolver Worker"]
        end
    end

    subgraph External ["External Data & Broker Services"]
        AngelAPI["AngelOne SmartAPI (REST & WS)"]
        LocalLLM["Local Ollama / LiteLLM Pipeline"]
    end

    subgraph Persistence ["Persistence Layer"]
        SQLite[("SQLite / Supabase Postgres DB")]
    end

    UI <-->|REST / WebSockets| API
    API --> Signals
    AgentDaemon --> QualityEngine
    AgentDaemon --> CapitalAlloc
    AgentDaemon --> Governance
    AgentDaemon --> AngelAPI
    Resolver --> AngelAPI
    Resolver --> SQLite
    API --> SQLite
```

*For detailed sequence diagrams and component specifications, check [architecture.md](architecture.md).*

---

## Bot Execution Pipeline

```mermaid
flowchart LR
    Scan([Market Scan 09:15 AM]) --> Indicators[Vectorized Indicators]
    Indicators --> VWAPCheck{VWAP Veto Aligned?}
    VWAPCheck -->|No| Veto[Signal Vetoed]
    VWAPCheck -->|Yes| Quality[Trade Quality Score >= 70]
    Quality --> Alloc[Capital Allocator Position Sizing]
    Alloc --> Governance{Max Drawdown Safe?}
    Governance -->|Safe| Execute[Execute via Broker API]
    Governance -->|Unsafe| Halt[Kill-Switch Triggered]
    Execute --> Resolver[Prediction Resolver Monitor]
```

---

## API Reference

### 1. Authentication & Broker APIs
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/login` | Authenticate user & issue session token | No |
| `POST` | `/api/logout` | Invalidate active user session | Yes |
| `GET` | `/api/auth/verify` | Verify current session token validity | Yes |
| `POST` | `/api/angelone/login` | Connect to AngelOne SmartAPI broker | Yes |
| `GET` | `/api/angelone/status` | Check AngelOne connection state | Yes |

### 2. Market Data & Signals APIs
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/quote` | Fetch live quote & depth for symbol | Yes |
| `GET` | `/api/history` | Retrieve historical OHLCV candles | Yes |
| `GET` | `/api/search` | Symbol & contract search lookup | Yes |
| `GET` | `/api/market_brief` | Retrieve overall market state & regime | Yes |
| `POST` | `/api/scan` | Trigger real-time scanner across NIFTY50 | Yes |
| `GET` | `/api/signals` | List active technical scanner signals | Yes |
| `GET` | `/api/signal/{symbol}` | Fetch technical signal details for symbol | Yes |
| `POST` | `/api/allocate` | Calculate position sizing for signal | Yes |

### 3. Trade Predictions & Journal APIs
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/predictions` | Record new trade entry prediction | Yes |
| `GET` | `/api/predictions` | List active open and resolved trades | Yes |
| `GET` | `/api/predictions/stats` | Aggregated PnL, Win Rate, and metrics | Yes |
| `POST` | `/api/predictions/{id}/resolve` | Manually resolve open trade | Yes |
| `DELETE` | `/api/predictions/{id}` | Delete trade prediction record | Yes |
| `GET` | `/api/journal` | List user journal entries | Yes |
| `POST` | `/api/journal` | Create new trade journal log | Yes |
| `DELETE` | `/api/journal/{id}` | Delete journal log entry | Yes |

### 4. Backtest & Simulation APIs
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/backtest/run` | Execute historical backtest strategy | Yes |
| `GET` | `/api/backtest/stats` | Retrieve aggregate backtest performance | Yes |
| `GET` | `/api/backtest/history` | Retrieve backtest signal history | Yes |
| `POST` | `/api/backtest/reset` | Reset backtest data store | Yes (Admin) |

---

## Repository Structure

```directory
trade-ai/
├── backend/                  # FastAPI Python Backend
├── frontend/                 # React + Vite + Vanilla CSS Frontend
├── architecture.md           # Visual architecture & component specifications
├── routes.md                 # Route mapping documentation
├── CONTRIBUTING.md           # Development & PR guidelines
├── SECURITY.md               # Secret management & security policy
└── LICENSE                   # MIT License
```

---

## Local Setup & Quickstart

### 1. Backend Setup (`/backend`)
```bash
cd backend
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --port 8000
```

### 2. Frontend Setup (`/frontend`)
```bash
cd frontend
npm install
npm run dev
```

---

## Community & Security

- **Contributing**: Please see [CONTRIBUTING.md](CONTRIBUTING.md) for setup and pull request guidelines.
- **Security Policy**: For secret management standards and reporting security issues, view [SECURITY.md](SECURITY.md).
- **License**: Released under the [MIT License](LICENSE).
