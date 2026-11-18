# Trade.ai Integration Plan: 6 Trading Repositories

## Repository Analysis Summary

| Repo | Language | Type | Integration Approach |
|------|----------|------|---------------------|
| **Lean (QuantConnect)** | C# / Python | Algorithmic Trading Engine | Use Python Algorithm Framework, Indicators, Data |
| **Nautilus Trader** | Python / Rust | Professional Trading System | Core trading engine replacement |
| **TimesFM** | Python (PyTorch/Flax) | Time Series Forecasting | Price/volatility forecasting service |
| **Kronos** | Python (PyTorch) | Financial Time Series Model | Alternative forecasting model |
| **Day Trader Skill** | Python | Complete Trading Workflow | Already available as skills |
| **QuantDinger** | Python | Agentic Trading OS | MCP server for agentic operations |

---

## Phase 1: Core Infrastructure (Week 1)

### 1.1 Nautilus Trader Integration (Primary Engine)
- **Location**: `backend/app/services/nautilus_engine.py`
- **Components to integrate**:
  - `nautilus_trader.core` - Core engine, clock, event bus
  - `nautilus_trader.backtest` - Backtesting engine
  - `nautilus_trader.execution` - Order execution
  - `nautilus_trader.risk` - Risk management
  - `nautilus_trader.adapters` - Broker adapters (add AngelOne adapter)
  - `nautilus_trader.model` - Instruments, orders, events

### 1.2 Lean Python Indicators
- **Location**: `backend/app/indicators/lean_indicators.py`
- **Port**: Key indicators from Lean's `Indicators` namespace
- **Use**: Replace/augment current indicator calculations

### 1.3 Data Layer Unification
- Create unified data interface supporting:
  - Nautilus Trader data format
  - Lean data format
  - Current AngelOne/yfinance format

---

## Phase 2: Forecasting Services (Week 1-2)

### 2.1 TimesFM Integration
- **Location**: `backend/app/services/forecasting/timesfm_service.py`
- **Model**: `timesfm-forecasting` (2.5B params) or `timesfm3` (30B)
- **API**: REST endpoint `/api/forecast/timesfm`
- **Inputs**: Historical price/volume data
- **Outputs**: Point forecasts, quantile forecasts, covariates support

### 2.2 Kronos Integration
- **Location**: `backend/app/services/forecasting/kronos_service.py`
- **Model**: PyTorch-based financial transformer
- **API**: REST endpoint `/api/forecast/kronos`
- **Use**: Alternative/ensemble with TimesFM

### 2.3 Forecasting Ensemble Service
- **Location**: `backend/app/services/forecasting/ensemble.py`
- **Combine**: TimesFM + Kronos + current statistical models
- **Weighted**: Based on historical accuracy per symbol/timeframe

---

## Phase 3: Strategy & Workflow (Week 2)

### 3.1 Day Trader Skill Adoption
- **Already available** as skills in `.claude/skills/`
- **Integrate**: Scanner → Entry → Exit → Risk → Budget → Broker → Alerts workflow
- **Location**: `backend/app/services/trader_workflow.py`

### 3.2 QuantDinger MCP Server
- **Deploy**: QuantDinger MCP server as sidecar
- **Integrate**: Strategy development, backtesting, watchlist management
- **API**: MCP protocol for agentic operations

---

## Phase 4: API & Frontend (Week 2-3)

### 4.1 New API Endpoints
```
POST /api/forecast/timesfm          - TimesFM forecast
POST /api/forecast/kronos           - Kronos forecast
POST /api/forecast/ensemble         - Ensemble forecast
POST /api/backtest/nautilus         - Nautilus backtest
POST /api/backtest/lean             - Lean backtest
GET  /api/strategies/quantdinger    - QuantDinger strategies
POST /api/workflow/trader           - Full trader workflow
```

### 4.2 Frontend Components
- Forecasting panel (TimesFM/Kronos/Ensemble)
- Nautilus backtest runner
- QuantDinger strategy manager
- Trader workflow dashboard

---

## Implementation Order

1. **Install dependencies** for all repos
2. **Nautilus Trader** core engine wrapper
3. **Lean Indicators** Python port
4. **TimesFM** forecasting service
5. **Kronos** forecasting service
6. **Ensemble** forecasting
7. **QuantDinger** MCP server deployment
8. **API endpoints** for all services
9. **Frontend** components
10. **Integration tests**

---

## Dependency Requirements

### Core Python Packages
```txt
# Nautilus Trader
nautilus-trader[all]>=1.150

# Lean (Python)
# Lean Python is embedded, we'll copy indicators

# TimesFM
timesfm @ git+https://github.com/google-research/timesfm.git
# or pip install timesfm (if on PyPI)

# Kronos
torch>=2.0
transformers>=4.30
# Kronos from local

# QuantDinger
# MCP server from local
```

---

## Directory Structure After Integration

```
trade.ai/
├── backend/
│   ├── app/
│   │   ├── services/
│   │   │   ├── nautilus_engine.py          # NEW: Nautilus core wrapper
│   │   │   ├── lean_indicators.py          # NEW: Lean indicators port
│   │   │   ├── forecasting/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── timesfm_service.py      # NEW: TimesFM wrapper
│   │   │   │   ├── kronos_service.py       # NEW: Kronos wrapper
│   │   │   │   ├── ensemble.py             # NEW: Ensemble forecasting
│   │   │   │   └── base.py                 # Base forecasting interface
│   │   │   ├── trader_workflow.py          # NEW: Day trader workflow
│   │   │   └── quantdinger_client.py       # NEW: QuantDinger MCP client
│   │   ├── api/v1/
│   │   │   ├── forecasting.py              # NEW: Forecast endpoints
│   │   │   ├── backtest.py                 # ENHANCED: Nautilus/Lean backtest
│   │   │   └── workflow.py                 # NEW: Trader workflow
│   │   └── core/
│   │       └── data_adapter.py             # NEW: Unified data layer
│   └── integrations/                       # Copied/referenced from integrations/
│       ├── lean_indicators/
│       ├── nautilus_trader/
│       ├── timesfm/
│       ├── kronos/
│       └── quantdinger/
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── ForecastingPanel.jsx        # NEW
│       │   ├── NautilusBacktestPanel.jsx   # NEW
│       │   ├── QuantDingerPanel.jsx        # NEW
│       │   └── TraderWorkflowPanel.jsx     # NEW
│       └── api.js                          # ENHANCED: New endpoints
└── integrations/                           # Git submodules or copied
    ├── Lean/
    ├── nautilus_trader/
    ├── timesfm/
    ├── Kronos/
    ├── day-trader-skill/
    └── QuantDinger/
```